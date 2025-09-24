import datetime

from app.models import Booking


def test_repr_function() -> None:
    booking = Booking(unit_id="1", guest_name="GuestA", check_in_date=datetime.date(2025, 9, 10), number_of_nights=5)
    assert (
        str(booking) == "BookingModel(id=None, guest_name='GuestA', unit_id='1', "
        "check_in_date=datetime.date(2025, 9, 10), number_of_nights=5)"
    )
