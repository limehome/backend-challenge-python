import datetime
from typing import Tuple

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


def extend_booking(db: Session, booking_id: int, new_number_of_nights: int) -> models.Booking | None:
    booking = db.get(models.Booking, booking_id)
    if booking is None:
        return None
    if new_number_of_nights <= booking.number_of_nights:
        raise UnableToBook('Extension must increase the number of nights')
    if unit_has_overlap(
        db,
        unit_id=booking.unit_id,
        check_in_date=booking.check_in_date,
        number_of_nights=new_number_of_nights,
        exclude_booking_id=booking.id,
    ):
        raise UnableToBook('The extended stay would overlap an existing booking')
    booking.number_of_nights = new_number_of_nights
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

    # check 3 : Unit is available for the requested date range
    if unit_has_overlap(db, booking.unit_id, booking.check_in_date, booking.number_of_nights):
        return False, 'For the given check-in date, the unit is already occupied'

    return True, 'OK'


def unit_has_overlap(db: Session, unit_id: str, check_in_date: datetime.date, number_of_nights: int, exclude_booking_id: int | None = None) -> bool:
    new_booking_check_out = check_in_date + datetime.timedelta(days=number_of_nights)
    existing_bookings = db.execute(
        select(models.Booking).where(models.Booking.unit_id == unit_id)
    ).scalars().all()
    for existing_booking in existing_bookings:
        if existing_booking.id == exclude_booking_id:
            continue
        existing_booking_check_out = existing_booking.check_in_date + datetime.timedelta(days=existing_booking.number_of_nights)
        if check_in_date < existing_booking_check_out and existing_booking.check_in_date < new_booking_check_out:
            return True
    return False
