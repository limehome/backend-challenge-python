import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guest_name: str
    unit_id: str
    check_in_date: datetime.date
    number_of_nights: int = Field(gt=0)


class BookingResponse(BookingBase):
    id: int = Field(description="Booking ID", repr=False)


class BookingPatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    number_of_nights: int = Field(gt=1)
