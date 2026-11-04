# Movie Tickets (movie_tickets)

A custom Frappe v16 application for managing movie ticket bookings across multiple theaters, screens, and shows with seat-based ticketing, race-condition safe bookings, and automated cancellation/refund rules.

---

## Features Implemented (Day 1)

### 1. Master & Core DocTypes
- **Movie Genre (`Movie Genre`)**:
  - Autonamed by genre name (`field:genre_name`).
  - Server-side case-insensitive duplicate genre validation.
- **Movie (`Movie`)**:
  - Naming series: `MOV-.#####`.
  - Auto-generated URL slug on `before_save` (`title` -> kebab-case slug).
  - Dynamic `movie_status` calculation (`Upcoming`, `Now Showing`, `Ended`) based on `release_date`, `end_date`, and `today()`.
  - Validations: `duration_minutes` (1 to 600), `end_date > release_date`.
- **Theater (`Theater`)**:
  - Autonamed by theater name (`field:theater_name`).
  - Auto-calculated `total_screens` tracking linked active screens.
- **Screen (`Screen`)**:
  - Autonamed by `{theater}-{screen_name}`.
  - Server-side validation: `total_seats == seat_rows * seats_per_row`.
  - Automatic recalculation of parent `Theater.total_screens` on insert/update/delete.
- **Show (`Show`)**:
  - Naming series: `SHW-.YYYY.-.#####`.
  - `before_insert`:
    - Auto-calculation of `end_time` using Python `datetime` (`start_time + movie.duration_minutes`).
    - Default `ticket_price` fetched from `Screen.base_price`.
    - Initial `available_seats` set to `Screen.total_seats`, `booked_seats = 0`.
  - `validate`:
    - Showtime conflict detection: prevents overlapping shows on the same screen and show date (`Screen {screen} already has a show scheduled from {existing_start} to {existing_end} on {show_date}.`).
    - Validates `show_date` is not in the past (allows today).
    - Validates movie's `movie_status` is not `Ended`.
  - `on_update`:
    - Auto-cancels related bookings with reason `"Show Cancelled"`, setting 100% refund when a show is marked `Cancelled`.

### 2. Transactional Booking Lifecycle
- **Ticket Booking (`Ticket Booking`)**:
  - Submittable DocType with naming series `BKG-.YYYY.-.#####`.
  - Child Table: `Booked Seat` (`seat_label`, `row_letter`, `seat_number`, `seat_price`).
  - `validate`:
    - Ensures show is `Scheduled` or `Now Playing`.
    - Validates seat label format `ROW-NUMBER` (e.g. `A-12`).
    - Validates row letter and seat number are within screen bounds.
    - Prevents duplicate seats within same booking.
    - Enforces seat limit (max 10, configurable via `Booking Configuration`).
    - Checks seat availability against existing pending/confirmed bookings for the show.
    - Real-time total calculation.
  - `on_submit`:
    - Sets `booking_status` to `Confirmed` and `payment_status` to `Paid`.
    - Increments `booked_seats` and decrements `available_seats` on `Show`.
  - `on_cancel`:
    - Sets `booking_status` to `Cancelled`.
    - Time-tiered refund calculation (using settings from `Booking Configuration`):
      - `> 4 hours` before show: 100% refund.
      - `2 to 4 hours` before show: 50% refund.
      - `< 2 hours` before show: 0% refund.
    - Sets `refund_amount`, `payment_status = "Refunded"`, and `cancellation_time = now_datetime()`.
    - Restores show's `available_seats` and decrements `booked_seats`.

### 3. Single DocType & Configuration
- **Booking Configuration (`Booking Configuration`)**:
  - Configurable parameters: `max_seats_per_booking`, `booking_expiry_minutes`, `full_refund_hours`, `partial_refund_hours`, `partial_refund_pct`, `enable_auto_expiry`, `booking_open_days_before`.
  - Loaded and utilized by controllers dynamically.

### 4. Fixtures & Customizations
- Custom field `booking_source` (`Counter`/`Website`/`App`, default `Website`) added to `Ticket Booking`.
- Property Setters for default list view sorting on `Show`.
- Exported fixtures in `movie_tickets/fixtures/custom_field.json` and `property_setter.json` registered in `hooks.py`.

---

## Running Unit Tests

Run all 9 unit tests with:
```bash
bench --site cinema.localhost run-tests --app movie_tickets
```

### Test Suite Summary:
1. `test_booking_decreases_available_seats`: Verifies show availability decreases on booking submission.
2. `test_cannot_book_already_taken_seat`: Verifies double-booking prevention.
3. `test_cannot_book_for_cancelled_show`: Verifies bookings cannot be made for cancelled shows.
4. `test_max_seats_per_booking_limit`: Enforces max seat limit per booking.
5. `test_full_refund_on_early_cancellation`: Verifies 100% refund for cancellation > 4 hours prior.
6. `test_partial_refund_on_late_cancellation`: Verifies 50% refund for cancellation 2-4 hours prior.
7. `test_no_refund_on_very_late_cancellation`: Verifies 0% refund for cancellation < 2 hours prior.
8. `test_show_conflict_validation`: Verifies overlapping shows on the same screen/date are blocked.
9. `test_cancel_restores_seats`: Verifies cancelling a booking restores available seats.
