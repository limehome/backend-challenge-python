# Challenge Notes

## Bug Fix

File: 'app/crud.py' - 'is_booking_possible()', check 3

Problem: The original check only blocked bookings with the exact same 'check_in_date'.
It had no awareness of booking duration, so a guest booked for 5 nights (e.g. May 21–25)
would not block another guest from checking in on May 22 - causing a double booking.

Fix: Replaced the exact-date comparison with a standard date-range overlap predicate:

-> Two bookings conflict when 'existing.check_in < new.checkout AND existing.checkout > new.check_in'

Since SQLite doesn't support date + integer arithmetic natively in SQLAlchemy filter
expressions, the overlap check fetches same-unit bookings and evaluates the predicate in
Python. On PostgreSQL this would be a single filtered SQL query with proper date functions.


## New Feature: Extend Stay

Endpoint: 'PATCH /api/v1/booking/{booking_id}/extend'

Request body:
'''json
{ "additional_nights": 3 }
'''

Logic:
- Fetches the existing booking by ID (returns 400 if not found)
- Constructs a virtual extended booking and runs it through 'is_booking_possible()',
  excluding the current booking from conflict checks (so it doesn't conflict with itself)
- If the extended period is free, updates 'number_of_nights' in place

## Trade-offs & What I'd improve with more time

- Return 404 for missing bookings - currently returns 400, a missing
  resource should be 404
- Push overlap check into SQL - on Postgres, use a proper date range query with an
  index on '(unit_id, check_in_date)' for performance at scale
- Add a computed 'check_out_date' column - would simplify overlap queries and make
  the API response more useful to clients
- Input validation - reject 'number_of_nights < 1', 'additional_nights < 1', and
  'check_in_date' in the past
- 'UnableToExtend' → proper HTTP 404 - split "not found" from "business rule
  violation" into separate exception types