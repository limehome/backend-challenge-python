import datetime
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas


class UnableToBook(Exception):
    pass


class UnableToExtend(Exception):
    pass


def create_booking(db: Session, booking: schemas.BookingBase) -> models.Booking:
    is_possible, reason = is_booking_possible(db=db, booking=booking)
    if not is_possible:
        raise UnableToBook(reason)
    db_booking = models.Booking(
        guest_name=booking.guest_name,
        unit_id=booking.unit_id,
        check_in_date=booking.check_in_date,
        number_of_nights=booking.number_of_nights,
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


def is_booking_possible(db: Session, booking: schemas.BookingBase, exclude_booking_id: int | None = None) -> Tuple[bool, str]:
    # check 1 : The same guest cannot book the same unit multiple times
    query = select(models.Booking).where(
        models.Booking.guest_name == booking.guest_name,
        models.Booking.unit_id == booking.unit_id,
        )
    if exclude_booking_id:
        query = query.where(models.Booking.id != exclude_booking_id)
    if db.execute(query).scalars().first():
        return False, 'The given guest name cannot book the same unit multiple times'

    # check 2 : The same guest cannot be in multiple units at the same time
    query = select(models.Booking).where(models.Booking.guest_name == booking.guest_name)
    if exclude_booking_id:
        query = query.where(models.Booking.id != exclude_booking_id)
    if db.execute(query).scalars().first():
        return False, 'The same guest cannot be in multiple units at the same time'

    # check 3 : Unit must be free for the entire requested period (overlap check)
    # A conflict exists when: existing.check_in < new.checkout AND existing.checkout > new.check_in
    new_checkout = booking.check_in_date + datetime.timedelta(days=booking.number_of_nights)

    # SQLite doesn't support date arithmetic natively in SQLAlchemy expressions easily,
    # so we fetch only same-unit bookings and filter them in Python. In a production environment with a more powerful DB, the above query would be preferred.
    same_unit_bookings = db.execute(
        select(models.Booking).where(
            models.Booking.unit_id == booking.unit_id,
            )
    ).scalars().all()

    if exclude_booking_id:
        same_unit_bookings = [b for b in same_unit_bookings if b.id != exclude_booking_id]

    for existing in same_unit_bookings:
        existing_checkout = existing.check_in_date + datetime.timedelta(days=existing.number_of_nights)
        if existing.check_in_date < new_checkout and existing_checkout > booking.check_in_date:
            return False, 'For the given check-in date, the unit is already occupied'

    return True, 'OK'


def extend_booking(db: Session, booking_id: int, additional_nights: int) -> models.Booking:
    booking = db.execute(
        select(models.Booking).where(models.Booking.id == booking_id)
    ).scalars().first()

    if not booking:
        raise UnableToExtend('Booking not found')

    extended = schemas.BookingBase(
        guest_name=booking.guest_name,
        unit_id=booking.unit_id,
        check_in_date=booking.check_in_date,
        number_of_nights=booking.number_of_nights + additional_nights,
    )

    is_possible, reason = is_booking_possible(db=db, booking=extended, exclude_booking_id=booking_id)
    if not is_possible:
        raise UnableToExtend(f'Cannot extend booking: {reason}')

    booking.number_of_nights += additional_nights
    db.commit()
    db.refresh(booking)
    return booking