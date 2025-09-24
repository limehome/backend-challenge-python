from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.crud import UnableToBook
from app.database import get_db
from app.models import Booking

router = APIRouter(prefix="/api/v1/booking", tags=["booking"])


@router.post(
    path="/",
    response_model=schemas.BookingResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "Booking successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "guest_name": "Guest4",
                        "unit_id": "6",
                        "check_in_date": "2025-11-30",
                        "number_of_nights": 5,
                        "id": 1,
                    }
                }
            },
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Failed to create booking",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "type": "missing",
                            "loc": ["body", "unit_id"],
                            "msg": "Field required",
                            "input": {"guest_name": "Guest4", "check_in_date": "2025-11-30", "number_of_nights": 5},
                        }
                    }
                }
            },
        },
    },
)
def create_booking(booking: schemas.BookingBase, db: Annotated[Session, Depends(get_db)]) -> Booking:
    """
    Create a new booking with the specified details.

    This endpoint adds a new booking to the system for a given guest, unit, check-in date,
    and number of nights. It validates that the booking is possible according to the
    business rules, such as unit availability and guest constraints.

    - **booking**: A `BookingBase` object containing the guest name, unit ID, check-in date,
      and number of nights.
    - **db**: The database session dependency.

    - **return**: `BookingResponse` — an object representing the newly created booking,
      including its unique ID.
    - **raises HTTPException**: Returns a 400 BAD REQUEST if the booking cannot be created,
      for example, if the unit is already occupied or the same guest tries to book the same
      unit multiple times.
    """
    try:
        return crud.create_booking(db=db, booking=booking)
    except UnableToBook as unable_to_book:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(unable_to_book)) from unable_to_book


@router.patch(
    path="/{booking_id}",
    response_model=schemas.BookingPatch,
    responses={
        status.HTTP_200_OK: {
            "description": "Booking successfully patched",
            "content": {"application/json": {"example": {"detail": {"number_of_nights": 10}}}},
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Failed to create booking",
            "content": {
                "application/json": {
                    "example": {"detail": "Number of nights must be greater than current number of nights '10'"}
                }
            },
        },
    },
)
def patch_booking(booking_id: int, booking: schemas.BookingPatch, db: Annotated[Session, Depends(get_db)]) -> Booking:
    """
    Patch an existing booking with updated information.

    This endpoint updates a booking's details, such as the number of nights, for a given booking ID.
    It validates the request and ensures that the updated booking information is allowed.

    - **booking_id**: The unique identifier of the booking to be patched.
    - **booking**: A `BookingPatch` object containing the fields to update.
    - **db**: The database session dependency.

    - **return**: An object representing the updated booking details, including any patched fields.
    - **raises HTTPException**: Returns a 400 BAD REQUEST if the booking cannot be updated,
      for example when the number of nights is invalid.
    """
    try:
        return crud.patch_booking(db=db, booking_id=booking_id, booking=booking)
    except UnableToBook as unable_to_book:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(unable_to_book)) from unable_to_book
