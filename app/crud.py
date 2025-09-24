from datetime import timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from . import models, schemas


class UnableToBook(Exception):
    pass


def create_booking(db: Session, booking: schemas.BookingBase) -> models.Booking:
    """
    Create a new booking in the database.

    This function validates if a booking request is possible according
    to business rules (unit availability, guest constraints). If valid, it
    inserts a new booking record into the database and returns it.

    - **db**: The active SQLAlchemy session.
    - **booking**: A `BookingBase` object containing guest name, unit ID,
      check-in date, and number of nights.

    - **return**: A `Booking` model instance representing the newly created booking.
    - **raises UnableToBook**: If the booking request violates business rules,
      such as the unit being unavailable or the same guest double-booking.
    """
    (is_possible, reason) = is_booking_possible(db=db, booking=booking)
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


def patch_booking(db: Session, booking_id: int, booking: schemas.BookingPatch) -> models.Booking:
    """
    Update an existing booking with new information.

    This function fetches an existing booking by ID, validates that the
    requested update is possible (e.g., extending nights without conflicts),
    and applies the update.

    - **db**: The active SQLAlchemy session.
    - **booking_id**: The unique identifier of the booking to update.
    - **booking**: A `BookingPatch` object containing the new number of nights.

    - **return**: A `Booking` model instance with updated values.
    - **raises UnableToBook**: If the booking does not exist or if the update
      request violates business rules (e.g., overlapping reservations).
    """
    booking_by_id: models.Booking | None = db.get(models.Booking, ident=booking_id)
    if not booking_by_id:
        raise UnableToBook("".join(["Booking with id: '", str(booking_id), "' does not exist."]))

    (is_possible, reason) = is_booking_update_possible(db=db, booking_by_id=booking_by_id, updated_booking=booking)
    if not is_possible:
        raise UnableToBook(reason)

    booking_by_id.number_of_nights = booking.number_of_nights
    db.commit()
    return booking_by_id


def is_booking_update_possible(
    db: Session,
    booking_by_id: models.Booking,
    updated_booking: schemas.BookingPatch,
) -> tuple[bool, str]:
    """
    Check whether a booking update is allowed.

    This function enforces business rules for extending an existing booking.
    It ensures that the number of nights is increased and that
    the unit is available during the extended period.

    - **db**: The active SQLAlchemy session.
    - **booking_by_id**: The current `Booking` model instance in the database.
    - **updated_booking**: A `BookingPatch` object containing the updated fields.

    - **return**: A tuple `(is_possible, reason)` where:
        - `is_possible`: `True` if the update can proceed, otherwise `False`.
        - `reason`: A human-readable explanation of the result.
    """
    # check 1: The guest extends time, not reduces.
    if updated_booking.number_of_nights <= booking_by_id.number_of_nights:
        return False, (
            f"Number of nights must be greater than current number of nights '{booking_by_id.number_of_nights}'"
        )

    # check 2: The unit is available in an extended period.
    check_out_date = booking_by_id.check_in_date + timedelta(days=updated_booking.number_of_nights)

    # The SQL statement BETWEEN is generally not recommended to be used. Especially with DATETIME
    # types. A more transparent, non-inclusive comparison is used instead.
    is_unit_occupied_stmt = select(models.Booking).where(
        models.Booking.unit_id == booking_by_id.unit_id,
        models.Booking.check_in_date > booking_by_id.check_in_date,
        models.Booking.check_in_date < check_out_date,
    )

    is_unit_occupied = db.execute(is_unit_occupied_stmt).scalars().first()
    if is_unit_occupied:
        return False, "For the given extended count of nights, the unit is already occupied"

    return True, "OK"


def is_booking_possible(db: Session, booking: schemas.BookingBase) -> tuple[bool, str]:
    """
    Check whether a new booking request is valid.

    This function enforces business rules for creating a booking:
    - The same guest cannot book the same unit multiple times with overlapping dates.
    - The same guest cannot stay in multiple units at the same time.
    - The unit must be available for the requested check-in date and duration.

    - **db**: The active SQLAlchemy session.
    - **booking**: A `BookingBase` object containing the new booking details.

    - **return**: A tuple `(is_possible, reason)` where:
        - `is_possible`: `True` if the booking is valid, otherwise `False`.
        - `reason`: A human-readable explanation of the validation result.
    """

    # SQL statement to filter rows by a range of days.
    # Since the database stores the number of nights instead of the check-out date,
    # it is necessary to calculate the check-out date and compare it with the desired date.
    # The SQLite-specific `julianday` function is used because there is no standard SQL construct for this.
    date_intersected_stmt = or_(
        and_(
            models.Booking.check_in_date <= booking.check_in_date,
            func.julianday(booking.check_in_date) - func.julianday(models.Booking.check_in_date)
            < models.Booking.number_of_nights,
        ),
        and_(
            booking.check_in_date <= models.Booking.check_in_date,
            func.julianday(models.Booking.check_in_date) - func.julianday(booking.check_in_date)
            < booking.number_of_nights,
        ),
    )

    # check 1: The same guest cannot book the same unit multiple times
    is_same_guest_booking_same_unit_stmt = select(models.Booking).where(
        models.Booking.guest_name == booking.guest_name,
        models.Booking.unit_id == booking.unit_id,
        date_intersected_stmt,
    )
    is_same_guest_booking_same_unit = db.execute(is_same_guest_booking_same_unit_stmt).scalars().first()

    if is_same_guest_booking_same_unit:
        return False, "The given guest name cannot book the same unit multiple times"

    # check 2: The same guest cannot be in multiple units at the same time
    is_same_guest_already_booked_stmt = select(models.Booking).where(
        models.Booking.guest_name == booking.guest_name,
        date_intersected_stmt,
    )
    is_same_guest_already_booked = db.execute(is_same_guest_already_booked_stmt).scalars().first()

    if is_same_guest_already_booked:
        return False, "The same guest cannot be in multiple units at the same time"

    # check 3: Unit is available for the check-in date
    is_unit_unavailable_on_check_in_date_stmt = select(models.Booking).where(
        date_intersected_stmt,
        models.Booking.unit_id == booking.unit_id,
    )

    is_unit_unavailable_on_check_in_date = db.execute(is_unit_unavailable_on_check_in_date_stmt).scalars().first()

    if is_unit_unavailable_on_check_in_date:
        return False, "For the given check-in date, the unit is already occupied"

    return True, "OK"
