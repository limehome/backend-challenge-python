import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app, get_db

Path("data").mkdir(parents=True, exist_ok=True)
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

GUEST_A_UNIT_1: dict = {
    'unit_id': '1', 'guest_name': 'GuestA', 'check_in_date': datetime.date.today().strftime('%Y-%m-%d'),
    'number_of_nights': 5
}
GUEST_A_UNIT_2: dict = {
    'unit_id': '2', 'guest_name': 'GuestA', 'check_in_date': datetime.date.today().strftime('%Y-%m-%d'),
    'number_of_nights': 5
}
GUEST_B_UNIT_1: dict = {
    'unit_id': '1', 'guest_name': 'GuestB', 'check_in_date': datetime.date.today().strftime('%Y-%m-%d'),
    'number_of_nights': 5
}


@pytest.fixture()
def test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.mark.freeze_time('2023-05-21')
def test_create_fresh_booking(test_db):
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    response.raise_for_status()
    assert response.status_code == 200, response.text


@pytest.mark.freeze_time('2023-05-21')
def test_same_guest_same_unit_booking(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text
    response.raise_for_status()

    # Guests want to book same unit again
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'The given guest name cannot book the same unit multiple times'


@pytest.mark.freeze_time('2023-05-21')
def test_same_guest_different_unit_booking(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # Guest wants to book another unit
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_2
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'The same guest cannot be in multiple units at the same time'


@pytest.mark.freeze_time('2023-05-21')
def test_different_guest_same_unit_booking(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # GuestB trying to book a unit that is already occuppied
    response = client.post(
        "/api/v1/booking",
        json=GUEST_B_UNIT_1
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'For the given check-in date, the unit is already occupied'


@pytest.mark.freeze_time('2023-05-21')
def test_different_guest_same_unit_booking_different_date(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # GuestB trying to book a unit that is already occuppied
    response = client.post(
        "/api/v1/booking",
        json={
            'unit_id': '1',  # same unit
            'guest_name': 'GuestB',  # different guest
            # check_in date of GUEST A + 1, the unit is already booked on this date
            'check_in_date': (datetime.date.today() + datetime.timedelta(1)).strftime('%Y-%m-%d'),
            'number_of_nights': 5
        }
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'For the given check-in date, the unit is already occupied'


@pytest.mark.freeze_time('2023-05-21')
def test_extend_booking_success(test_db):
    # Create a booking, then extend it from 5 to 7 nights
    response = client.post(
        "/api/v1/booking", 
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text
    booking_id = response.json()['id']

    response = client.post(
        f"/api/v1/booking/{booking_id}/extend",
        json={'number_of_nights': 7},
    )
    assert response.status_code == 200, response.text
    assert response.json()['number_of_nights'] == 7
    assert response.json()['id'] == booking_id


@pytest.mark.freeze_time('2023-05-21')
def test_extend_booking_not_found(test_db):
    response = client.post(
        "/api/v1/booking/999/extend",
        json={'number_of_nights': 7},
    )
    assert response.status_code == 404, response.text
    assert response.json()['detail'] == 'Booking not found'


@pytest.mark.freeze_time('2023-05-21')
def test_extend_booking_with_false_number_of_nights(test_db):
    create_response = client.post(
        "/api/v1/booking", 
        json=GUEST_A_UNIT_1
    )
    assert create_response.status_code == 200, create_response.text
    booking_id = create_response.json()['id']

    # Same number of nights should be rejected
    response = client.post(
        f"/api/v1/booking/{booking_id}/extend",
        json={'number_of_nights': 5},
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'Extension must increase the number of nights'

    # Fewer nights is also rejected
    response = client.post(
        f"/api/v1/booking/{booking_id}/extend",
        json={'number_of_nights': 4},
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'Extension must increase the number of nights'


@pytest.mark.freeze_time('2023-05-21')
def test_extend_booking_with_overlap(test_db):
    # GuestA takes Unit 1 for 5 nights
    response = client.post(
        "/api/v1/booking", 
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text
    booking_id = response.json()['id']

    # GuestB takes Unit 1 starting today+5 nights (allowed)
    response = client.post(
        "/api/v1/booking",
        json={
            'unit_id': '1',
            'guest_name': 'GuestB',
            'check_in_date': (datetime.date.today() + datetime.timedelta(5)).strftime('%Y-%m-%d'),
            'number_of_nights': 3,
        },
    )
    assert response.status_code == 200, response.text

    # GuestA tries to extend to 6 nights which would overlap with GuestB's stay
    response = client.post(
        f"/api/v1/booking/{booking_id}/extend",
        json={'number_of_nights': 6},
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'The extended stay would overlap an existing booking'
