# Handover Notes

## What was changed

- Fixed the booking overlap bug in `app/crud.py`.
  - The old logic only checked `check_in_date`.
  - The new logic checks the full stay interval and rejects overlapping bookings for the same unit.

- Added support for extending an existing booking.
  - New API route: `PATCH /api/v1/booking/{booking_id}/extend`
  - New request schema: `BookingExtendRequest` in `app/schemas.py`
  - New business rule: extension is only allowed if the new stay period does not overlap another booking for the same unit.

- Stabilized and expanded tests in `app/test_bookings.py`.
  - Ensured the suite is deterministic by using fixed test dates.
  - Added coverage for:
    - booking overlap detection
    - adjacent booking allowance
    - successful booking extension
    - conflicting booking extension

## How to run

- Start the application:

```bash
docker compose up
```

- Run the booking tests:

```bash
python -m pytest app/test_bookings.py -v
```

## Notes

- The current solution keeps the API simple and uses the existing booking model.
- The extension logic reuses the same overlap detection approach as new bookings.
- This avoids double-booking a unit while still allowing guests to extend an active reservation when the unit remains available.
