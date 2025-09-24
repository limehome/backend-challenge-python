from collections.abc import Generator
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db() -> Generator[Session, Any]:
    db = None
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        if db:
            db.close()


app.dependency_overrides[get_db] = override_get_db
FROZEN_DATE = date(year=2025, month=9, day=24)
client = TestClient(app)

GUEST_A_UNIT_1: dict = {
    "unit_id": "1",
    "guest_name": "GuestA",
    "check_in_date": FROZEN_DATE.strftime("%Y-%m-%d"),
    "number_of_nights": 5,
}


@pytest.fixture
def test_db() -> Generator[None, Any]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_create_fresh_booking(test_db: None) -> None:
    response = client.post("/api/v1/booking", json=GUEST_A_UNIT_1)
    response.raise_for_status()
    assert response.status_code == 200, response.text


GUEST_A_UNIT_1_ZERO_NIGHTS: dict = {
    "unit_id": "1",
    "guest_name": "GuestA",
    "check_in_date": FROZEN_DATE.strftime("%Y-%m-%d"),
    "number_of_nights": 0,
}


def test_create_zero_nights_booking(test_db: None) -> None:
    response = client.post("/api/v1/booking", json=GUEST_A_UNIT_1_ZERO_NIGHTS)
    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["loc"] == ["body", "number_of_nights"]
    assert response.json()["detail"][0]["msg"] == "Input should be greater than 0"


# fmt: off
TEST_CASES_SAME_USER_AND_UNIT_DATES_NOT_INTERSECTING = [
    (
        "1", "GuestA", FROZEN_DATE, 5,
        "1", "GuestA", FROZEN_DATE + timedelta(days=10), 5
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=10), 5,
        "1", "GuestA", FROZEN_DATE, 5
    ),

    # ToDo: Check if the following edge case must be processed differently.
    # User books the same unit at the day when he leaves it. Those are edge cases and
    # perhaps should be processed differently. For example return error that user must
    # extend booking instead of making the new one. Currently this case is accepted as valid
    (
        "1", "GuestA", FROZEN_DATE, 5,
        "1", "GuestA", FROZEN_DATE + timedelta(days=5), 5
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=5), 5,
        "1", "GuestA", FROZEN_DATE, 5
    ),
]

TEST_CASES_DIFFERENT_USER_SAME_UNIT_DATES_NOT_INTERSECTING = [
    (
        "1", "GuestA", FROZEN_DATE, 5,
        "1", "GuestB", FROZEN_DATE + timedelta(days=10), 5,
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=10), 5,
        "1", "GuestB", FROZEN_DATE, 5,
    ),
    (
        "1", "GuestA", FROZEN_DATE, 5,
        "1", "GuestB", FROZEN_DATE + timedelta(days=5), 5,
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=5), 5,
        "1", "GuestB", FROZEN_DATE, 5,
    ),
]

TEST_CASES_SAME_USER_DIFFERENT_UNITS_DATES_NOT_INTERSECTING = [
    (
        "1", "GuestA", FROZEN_DATE, 5,
        "2", "GuestA", FROZEN_DATE + timedelta(days=10), 5,
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=10), 5,
        "2", "GuestA", FROZEN_DATE, 5,
    ),
(
        "1", "GuestA", FROZEN_DATE, 5,
        "2", "GuestA", FROZEN_DATE + timedelta(days=5), 5,
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=5), 5,
        "2", "GuestA", FROZEN_DATE, 5,
    ),
]

TEST_CASES_DIFFERENT_USERS_DIFFERENT_UNITS_DATES_NOT_INTERSECTING = [
    (
        "1", "GuestA", FROZEN_DATE, 5,
        "2", "GuestB", FROZEN_DATE + timedelta(days=10), 5,
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=10), 5,
        "2", "GuestB", FROZEN_DATE, 5,
    ),
]

TEST_CASES_DIFFERENT_USERS_DIFFERENT_UNITS_DATES_INTERSECTING = [
    (
        "1", "GuestA", FROZEN_DATE, 5,
        "2", "GuestB", FROZEN_DATE + timedelta(days=2), 5,
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=3), 5,
        "2", "GuestB", FROZEN_DATE, 5,
    ),
    (
        "1", "GuestA", FROZEN_DATE, 10,
        "2", "GuestB", FROZEN_DATE + timedelta(days=2), 5,
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=3), 5,
        "2", "GuestB", FROZEN_DATE, 10,
    ),
]
# fmt: on
TEST_CASES_BOOKING_AVAILABLE = (
    TEST_CASES_SAME_USER_AND_UNIT_DATES_NOT_INTERSECTING
    + TEST_CASES_DIFFERENT_USER_SAME_UNIT_DATES_NOT_INTERSECTING
    + TEST_CASES_SAME_USER_DIFFERENT_UNITS_DATES_NOT_INTERSECTING
    + TEST_CASES_DIFFERENT_USERS_DIFFERENT_UNITS_DATES_NOT_INTERSECTING
    + TEST_CASES_DIFFERENT_USERS_DIFFERENT_UNITS_DATES_INTERSECTING
)


@pytest.mark.parametrize(
    (
        "first_unit_id",
        "first_guest_name",
        "first_check_in_date",
        "first_number_of_nights",
        "second_unit_id",
        "second_guest_name",
        "second_check_in_date",
        "second_number_of_nights",
    ),
    TEST_CASES_BOOKING_AVAILABLE,
)
def test_booking_available(
    test_db: None,
    first_unit_id: str,
    first_guest_name: str,
    first_check_in_date: date,
    first_number_of_nights: int,
    second_guest_name: str,
    second_unit_id: str,
    second_check_in_date: date,
    second_number_of_nights: int,
) -> None:
    response = client.post(
        "/api/v1/booking",
        json={
            "unit_id": first_unit_id,
            "guest_name": first_guest_name,
            "check_in_date": first_check_in_date.strftime("%Y-%m-%d"),
            "number_of_nights": first_number_of_nights,
        },
    )
    response.raise_for_status()
    assert response.status_code == 200, response.text

    response = client.post(
        "/api/v1/booking",
        json={
            "unit_id": second_unit_id,
            "guest_name": second_guest_name,
            "check_in_date": second_check_in_date.strftime("%Y-%m-%d"),
            "number_of_nights": second_number_of_nights,
        },
    )
    assert response.status_code == 200, response.text


# Intersecting dates for the same unit must prevent from booking no matter if user is the same or different
# fmt: off
TEST_CASES_SAME_UNITS_DATES_INTERSECTING = [
    (
        "1", "GuestA", FROZEN_DATE, 5,
        "1", "GuestA", FROZEN_DATE + timedelta(days=2), 5,
        "The given guest name cannot book the same unit multiple times"
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=3), 5,
        "1", "GuestA", FROZEN_DATE, 5,
        "The given guest name cannot book the same unit multiple times"
    ),
    (
        "1", "GuestA", FROZEN_DATE, 10,
        "1", "GuestA", FROZEN_DATE + timedelta(days=2), 5,
        "The given guest name cannot book the same unit multiple times"
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=3), 5,
        "1", "GuestA", FROZEN_DATE, 10,
        "The given guest name cannot book the same unit multiple times"
    ),
    (
        "1", "GuestA", FROZEN_DATE, 5,
        "1", "GuestB", FROZEN_DATE + timedelta(days=2), 5,
        "For the given check-in date, the unit is already occupied"
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=3), 5,
        "1", "GuestB", FROZEN_DATE, 5,
        "For the given check-in date, the unit is already occupied"
    ),
    (
        "1", "GuestA", FROZEN_DATE, 10,
        "1", "GuestB", FROZEN_DATE + timedelta(days=2), 5,
        "For the given check-in date, the unit is already occupied"
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=3), 5,
        "1", "GuestB", FROZEN_DATE, 10,
        "For the given check-in date, the unit is already occupied"
    ),
]

# Intersecting dates for the same user must prevent from booking different units
TEST_CASES_SAME_USER_DATES_INTERSECTING = [
    (
        "1", "GuestA", FROZEN_DATE, 5,
        "2", "GuestA", FROZEN_DATE + timedelta(days=2), 5,
        "The same guest cannot be in multiple units at the same time"
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=3), 5,
        "2", "GuestA", FROZEN_DATE, 5,
        "The same guest cannot be in multiple units at the same time"
    ),
    (
        "1", "GuestA", FROZEN_DATE, 10,
        "2", "GuestA", FROZEN_DATE + timedelta(days=2), 5,
        "The same guest cannot be in multiple units at the same time"
    ),
    (
        "1", "GuestA", FROZEN_DATE + timedelta(days=3), 5,
        "2", "GuestA", FROZEN_DATE, 10,
        "The same guest cannot be in multiple units at the same time"
    ),
]
# fmt: on
TEST_CASES_DATES_INTERSECTING = TEST_CASES_SAME_UNITS_DATES_INTERSECTING + TEST_CASES_SAME_USER_DATES_INTERSECTING


@pytest.mark.parametrize(
    (
        "first_unit_id",
        "first_guest_name",
        "first_check_in_date",
        "first_number_of_nights",
        "second_unit_id",
        "second_guest_name",
        "second_check_in_date",
        "second_number_of_nights",
        "expected_error_text",
    ),
    TEST_CASES_DATES_INTERSECTING,
)
def test_same_guest_intersected_dates(
    test_db: None,
    first_unit_id: str,
    first_guest_name: str,
    first_check_in_date: date,
    first_number_of_nights: int,
    second_unit_id: str,
    second_guest_name: str,
    second_check_in_date: date,
    second_number_of_nights: int,
    expected_error_text: str,
) -> None:
    response = client.post(
        "/api/v1/booking",
        json={
            "unit_id": first_unit_id,
            "guest_name": first_guest_name,
            "check_in_date": first_check_in_date.strftime("%Y-%m-%d"),
            "number_of_nights": first_number_of_nights,
        },
    )
    response.raise_for_status()
    assert response.status_code == 200, response.text

    response = client.post(
        "/api/v1/booking",
        json={
            "unit_id": second_unit_id,
            "guest_name": second_guest_name,
            "check_in_date": second_check_in_date.strftime("%Y-%m-%d"),
            "number_of_nights": second_number_of_nights,
        },
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == expected_error_text


####### Patch tests
def test_patch_existing_booking(test_db: None) -> None:
    response = client.post("/api/v1/booking", json=GUEST_A_UNIT_1)
    response.raise_for_status()
    assert response.status_code == 200, response.text
    response = client.patch("/api/v1/booking/1", json=GUEST_A_PATCH_UNIT_1)
    assert response.status_code == 200, response.text


GUEST_A_PATCH_UNIT_1: dict = {"number_of_nights": 6}


def test_patch_not_existing_booking(test_db: None) -> None:
    response = client.patch("/api/v1/booking/1", json=GUEST_A_PATCH_UNIT_1)
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Booking with id: '1' does not exist."


GUEST_A_PATCH_UNIT_1_5_NIGHTS: dict = {"number_of_nights": 5}


def test_patch_booking_with_same_number_of_nights(test_db: None) -> None:
    response = client.post("/api/v1/booking", json=GUEST_A_UNIT_1)
    response.raise_for_status()

    assert response.status_code == 200, response.text
    response = client.patch("/api/v1/booking/1", json=GUEST_A_PATCH_UNIT_1_5_NIGHTS)
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Number of nights must be greater than current number of nights '5'"


GUEST_A_PATCH_UNIT_1_OTHER_INFO: dict = {"guest_name": "GUEST_B"}


def test_patch_booking_with_unsupported_data(test_db: None) -> None:
    response = client.post("/api/v1/booking", json=GUEST_A_UNIT_1)
    response.raise_for_status()
    assert response.status_code == 200, response.text

    response = client.patch("/api/v1/booking/1", json=GUEST_A_PATCH_UNIT_1_OTHER_INFO)
    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["loc"] == ["body", "number_of_nights"]
    assert response.json()["detail"][0]["msg"] == "Field required"


GUEST_A_PATCH_UNIT_1_4_NIGHTS: dict = {"number_of_nights": 5}


def test_patch_booking_with_less_number_of_nights(test_db: None) -> None:
    response = client.post("/api/v1/booking", json=GUEST_A_UNIT_1)
    response.raise_for_status()
    assert response.status_code == 200, response.text

    response = client.patch("/api/v1/booking/1", json=GUEST_A_PATCH_UNIT_1_4_NIGHTS)
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Number of nights must be greater than current number of nights '5'"


# Not intersecting dates for the same unit must prevent from booking no matter if guest is the same or different.
# fmt: off
TEST_CASES_PATCH_SAME_UNITS_DATES_NOT_INTERSECTING = [
    ("GuestA", FROZEN_DATE, 5, "GuestB", FROZEN_DATE + timedelta(days=6), 5, 7),
    ("GuestA", FROZEN_DATE, 5, "GuestB", FROZEN_DATE + timedelta(days=5), 5, 7),
    ("GuestA", FROZEN_DATE + timedelta(days=10), 5, "GuestB", FROZEN_DATE, 5, 7),
    ("GuestA", FROZEN_DATE + timedelta(days=10), 5, "GuestB", FROZEN_DATE, 5, 10),
]
# fmt: on
@pytest.mark.parametrize(
    (
        "first_guest_name",
        "first_check_in_date",
        "first_number_of_nights",
        "second_guest_name",
        "second_check_in_date",
        "second_number_of_nights",
        "new_number_of_nights",
    ),
    TEST_CASES_PATCH_SAME_UNITS_DATES_NOT_INTERSECTING,
)
def test_patch_different_guest_not_intersected_dates(
    test_db: None,
    first_guest_name: str,
    first_check_in_date: date,
    first_number_of_nights: int,
    second_guest_name: str,
    second_check_in_date: date,
    second_number_of_nights: int,
    new_number_of_nights: int,
) -> None:
    unit_id: str = "1"
    response = client.post(
        "/api/v1/booking",
        json={
            "unit_id": unit_id,
            "guest_name": first_guest_name,
            "check_in_date": first_check_in_date.strftime("%Y-%m-%d"),
            "number_of_nights": first_number_of_nights,
        },
    )
    response.raise_for_status()
    assert response.status_code == 200, response.text

    response = client.post(
        "/api/v1/booking",
        json={
            "unit_id": unit_id,
            "guest_name": second_guest_name,
            "check_in_date": second_check_in_date.strftime("%Y-%m-%d"),
            "number_of_nights": second_number_of_nights,
        },
    )
    response.raise_for_status()
    booking_id = response.json()["id"]
    assert response.status_code == 200, response.text

    response = client.patch(f"/api/v1/booking/{booking_id}", json={"number_of_nights": new_number_of_nights})
    response.raise_for_status()
    assert response.status_code == 200, response.text
    assert response.json()["number_of_nights"] == new_number_of_nights


# Not intersecting dates for the same unit must prevent from booking no matter if guest is the same or different.
# fmt: off
TEST_CASES_PATCH_SAME_UNITS_DATES_INTERSECTING = [
    ("GuestA", FROZEN_DATE + timedelta(days=5), 5, "GuestB", FROZEN_DATE, 5, 7),
    ("GuestA", FROZEN_DATE + timedelta(days=6), 5, "GuestB", FROZEN_DATE, 5, 8),
    ("GuestA", FROZEN_DATE + timedelta(days=6), 5, "GuestB", FROZEN_DATE, 5, 20),

    # ToDo: Following cases are not mentioned in task. User has two booking and extends first one to cover both.
    # By good it should be special procedure to cancel the second one booking and update the first one.
    # Such use cases are out of scope.
    ("GuestA", FROZEN_DATE + timedelta(days=5), 5, "GuestA", FROZEN_DATE, 5, 7),
    ("GuestA", FROZEN_DATE + timedelta(days=6), 5, "GuestA", FROZEN_DATE, 5, 8),
    ("GuestA", FROZEN_DATE + timedelta(days=6), 5, "GuestA", FROZEN_DATE, 5, 20),
]
# fmt: on
@pytest.mark.parametrize(
    (
        "first_guest_name",
        "first_check_in_date",
        "first_number_of_nights",
        "second_guest_name",
        "second_check_in_date",
        "second_number_of_nights",
        "new_number_of_nights",
    ),
    TEST_CASES_PATCH_SAME_UNITS_DATES_INTERSECTING,
)
def test_patch_different_guest_intersected_dates(
    test_db: None,
    first_guest_name: str,
    first_check_in_date: date,
    first_number_of_nights: int,
    second_guest_name: str,
    second_check_in_date: date,
    second_number_of_nights: int,
    new_number_of_nights: int,
) -> None:
    unit_id: str = "1"
    response = client.post(
        "/api/v1/booking",
        json={
            "unit_id": unit_id,
            "guest_name": first_guest_name,
            "check_in_date": first_check_in_date.strftime("%Y-%m-%d"),
            "number_of_nights": first_number_of_nights,
        },
    )
    response.raise_for_status()
    assert response.status_code == 200, response.text

    response = client.post(
        "/api/v1/booking",
        json={
            "unit_id": unit_id,
            "guest_name": second_guest_name,
            "check_in_date": second_check_in_date.strftime("%Y-%m-%d"),
            "number_of_nights": second_number_of_nights,
        },
    )
    response.raise_for_status()
    booking_id = response.json()["id"]
    assert response.status_code == 200, response.text

    response = client.patch(f"/api/v1/booking/{booking_id}", json={"number_of_nights": new_number_of_nights})
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "For the given extended count of nights, the unit is already occupied"
