# Notes

## The bug fix

Check 3 in `is_booking_possible` was only matching bookings with the exact same `check_in_date`, so a second guest could book any day in the middle of someone else's stay causing `test_different_guest_same_unit_booking_different_date` test to fail. I changed it to check if there are any overlaps between two stays. There is an overlap if and only if `new.check_in < existing.check_out AND existing.check_in < new.check_out`.

It's a plain Python loop with `datetime.timedelta`, at this scale the loop seemed like the easiest implementation.

## The /extend endpoint

`POST /api/v1/booking/{id}/extend`, body `{"number_of_nights": N}` where `N` is the new total number of nights to be booked.

A few decisions worth flagging:

- Added a `Booking` response schema that includes `id` so clients can learn it on create. Felt cleaner than overloading `(guest_name, unit_id)` as a composite key.
- `new_total <= current` is rejected since the README says "extend".
- Pulled check 3 out into `unit_has_overlap()` so both create and extend use it. Extend passes `exclude_booking_id` so the row being extended doesn't look like it conflicts with itself.

## Running

```
docker compose run --rm api uv run pytest
```

9 tests should pass, 5 original plus 4 for `/extend`.
