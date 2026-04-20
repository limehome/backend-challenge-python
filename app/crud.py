from typing import Tuple
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas


class UnableToBook(Exception):
    pass


def create_booking(db: Session, booking: schemas.BookingBase) -> models.Booking:
    is_possible, reason = is_booking_possible(db=db, booking=booking)
    if not is_possible:
        raise UnableToBook(reason)
    db_booking = models.Booking(
        guest_name=booking.guest_name, unit_id=booking.unit_id,
        check_in_date=booking.check_in_date, number_of_nights=booking.number_of_nights)
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


def extend_booking(db: Session, booking_id: int, additional_nights: int) -> models.Booking:
    booking = db.execute(
        select(models.Booking).where(models.Booking.id == booking_id)
    ).scalars().first()
    if not booking:
        raise UnableToBook('Booking not found')
    if additional_nights <= 0:
        raise UnableToBook('Additional nights must be positive')

    new_number_of_nights = booking.number_of_nights + additional_nights
    new_check_in = booking.check_in_date
    new_check_out = booking.check_in_date + timedelta(days=new_number_of_nights)

    existing_bookings = db.execute(
        select(models.Booking).where(
            models.Booking.unit_id == booking.unit_id,
            models.Booking.id != booking_id,
        )
    ).scalars().all()

    for existing in existing_bookings:
        existing_check_out = existing.check_in_date + timedelta(days=existing.number_of_nights)
        if new_check_in < existing_check_out and existing.check_in_date < new_check_out:
            raise UnableToBook('The unit is already occupied during the requested dates')

    booking.number_of_nights = new_number_of_nights
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def is_booking_possible(db: Session, booking: schemas.BookingBase) -> Tuple[bool, str]:
    # check 1 : The Same guest cannot book the same unit multiple times
    if db.execute(
        select(models.Booking).where(
            models.Booking.guest_name == booking.guest_name,
            models.Booking.unit_id == booking.unit_id,
        )
    ).scalars().first():
        return False, 'The given guest name cannot book the same unit multiple times'

    # check 2 : the same guest cannot be in multiple units at the same time
    if db.execute(
        select(models.Booking).where(models.Booking.guest_name == booking.guest_name)
    ).scalars().first():
        return False, 'The same guest cannot be in multiple units at the same time'

    # check 3 : Unit is available for the entire booking period (no overlapping bookings)
    existing_bookings = db.execute(
        select(models.Booking).where(models.Booking.unit_id == booking.unit_id)
    ).scalars().all()
    
    new_check_in = booking.check_in_date
    new_check_out = booking.check_in_date + timedelta(days=booking.number_of_nights)
    
    for existing in existing_bookings:
        existing_check_out = existing.check_in_date + timedelta(days=existing.number_of_nights)
        # Check for overlap: two ranges [a,b) and [c,d) overlap if a < d and c < b
        if new_check_in < existing_check_out and existing.check_in_date < new_check_out:
            return False, 'For the given check-in date, the unit is already occupied'

    return True, 'OK'
