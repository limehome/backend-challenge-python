from http import HTTPStatus

from fastapi import FastAPI, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .crud import UnableToBook
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def hello_world():
    return {"message": "OK"}


@app.post("/api/v1/booking", response_model=schemas.Booking)
def create_booking(booking: schemas.BookingBase, db: Session = Depends(get_db)):
    try:
        return crud.create_booking(db=db, booking=booking)
    except UnableToBook as unable_to_book:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST,
                            detail=str(unable_to_book))


@app.post("/api/v1/booking/{booking_id}/extend", response_model=schemas.Booking)
def extend_booking(
    booking_id: int,
    payload: schemas.BookingExtension,
    db: Session = Depends(get_db),
):
    try:
        booking = crud.extend_booking(db, booking_id, payload.number_of_nights)
    except UnableToBook as unable_to_book:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST,
                            detail=str(unable_to_book))
    if booking is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='Booking not found')
    return booking
