from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Booking(Base):
    __tablename__ = "booking"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    guest_name: Mapped[str] = mapped_column(String, nullable=False)
    unit_id: Mapped[str] = mapped_column(String, nullable=False)
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    number_of_nights: Mapped[int] = mapped_column(nullable=False)

    def __repr__(self) -> str:
        return (
            f"BookingModel(id={self.id!r}, guest_name={self.guest_name!r}, unit_id={self.unit_id!r}, "
            f"check_in_date={self.check_in_date!r}, number_of_nights={self.number_of_nights!r})"
        )
