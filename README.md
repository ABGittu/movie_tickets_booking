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

## Features Implemented (Day 2)

### 1. Whitelisted APIs (`movie_tickets.api`)
- `get_seat_availability(show_name)`: Returns 2D seat matrix (`seat_grid`), dimensions, taken seats, and pricing.
- `create_booking(show, customer_name, customer_email, customer_phone, seats)`: Creates booking with child seat records and reserves seats.
- `get_shows_for_movie(movie, city=None, date=None)`: Fetches upcoming shows grouped by theater with availability counts.
- `send_booking_confirmation(booking_name)`: Dispatches confirmation email to customer.
- `get_revenue_summary(theater=None, from_date=None, to_date=None)`: Aggregates revenue, seats, bookings, and occupancy.
- `confirm_payment(booking_name)`: Submits pending unpaid bookings and marks them paid.
- `cancel_booking(booking_name, reason=None)`: Cancels booking and applies automatic time-tiered refund rules.

### 2. Web Portal & High-Contrast Light/Dark Theme
- `/now-showing`: Search bar, filter by showing status (`All`, `Now Showing`, `Upcoming`, `Ended`), genre, language, and "Only with Active Shows" toggle.
- `/movie-shows?movie=MOV-XXXXX`: Shows grouped by theater and dates, availability rules, and interactive Bootstrap seat booking modal.
- `/my-bookings`: Booking history with status tags, Pay Now, and Cancel Ticket flows.
- Global Theme Switcher (`cinema_theme.js` & `cinema_theme.css`): Persisted in `localStorage`, reactive across all pages and navbar, with true light mode (`#ffffff` / `#f8fafc`) and high-contrast dark mode (`#0b0f19` / `#131b2e`).

---

## Features Implemented (Day 3)

### 1. Task 3.1: Scheduled Background Jobs (`movie_tickets.tasks`)
- **`auto_expire_unpaid_bookings`** (cron: `*/5 * * * *`):
  Finds `Ticket Booking` records with `booking_status = 'Pending'` and `payment_status = 'Unpaid'` older than `booking_expiry_minutes` (configured in `Booking Configuration`), marks them `Expired`, and releases seats on the `Show`.
- **`update_movie_status`** (daily):
  Recalculates `movie_status` for all movies based on `today()` vs `release_date` and `end_date`.
- **`update_show_status`** (hourly):
  Transitions past-date shows to `Completed`, active shows to `Now Playing`, and finished shows to `Completed`.
- **`daily_revenue_digest`** (cron: `0 23 * * *`):
  Computes today's total confirmed bookings, revenue, and top-performing movie, then queues an HTML digest email to Cinema Managers.

### 2. Task 3.2: Hooks Configuration (`hooks.py`)
- **`doc_events`**:
  - `Ticket Booking.after_insert`: Sends "Booking Received" email to customer with payment deadline.
  - `Ticket Booking.on_submit`: Sends full confirmed booking details with theater, screen, seats, and amount.
  - `Movie.before_save`: Generates unique slug and updates `movie_status`.
- **`override_whitelisted_methods`**:
  - Overrides `frappe.client.get_count` with `movie_tickets.overrides.custom_get_count` to log audit events (`DocType` and filters queried) while delegating to the core implementation.
  - Documented with comprehensive conceptual commentary on use cases, risks, and alternatives.
- **`app_include_css` / `app_include_js`**:
  - `cinema.css`: Status badge colors, `.badge-houseful` pulsing animation, and seat availability color tokens for Desk.
  - `cinema.js`: Logs `"Movie Tickets App Loaded"` and binds `Ctrl+Shift+B` shortcut to open a new `Ticket Booking` form.

### 3. Task 3.3: Script Report — "Box Office Collection Report"
- Path: `movie_tickets/movie_tickets/report/box_office_collection_report/`
- Standard script report with columns:
  - Movie Title, Genre, Language, Total Shows, Total Bookings, Total Seats Sold, Total Revenue, Avg Occupancy (%), Avg Ticket Price.
- Filters:
  - Theater (`Link` to `Theater`)
  - Date Range (`from_date` to `to_date`)
  - Genre (`Link` to `Movie Genre`)
  - Language (`Select`)
- Charts:
  - Chart 1: Bar chart displaying Top 10 movies by revenue.
  - Chart 2: Donut/Pie chart displaying revenue contribution by screen type (`Standard`, `IMAX`, `3D`, `4DX`).
  - Interactive toolbar buttons allowing instant chart switching in Desk report view.
- Executive summary indicators:
  - Total Box Office Revenue, Total Seats Sold, Total Bookings, and Avg Ticket Price.

### 4. Task 3.4: Data Migration Patches
All patches registered in `movie_tickets/patches.txt` and executed via `bench migrate`:
1. `movie_tickets.patches.v1_0.recalculate_show_seat_counts`: Recalculated `booked_seats` and `available_seats` across all shows from confirmed bookings.
2. `movie_tickets.patches.v1_0.set_movie_slugs`: Populated slug for all movies based on title.
3. `movie_tickets.patches.v1_0.populate_booking_source`: Initialized custom field `booking_source = "Counter"` for legacy bookings.
4. `movie_tickets.patches.v1_0.generate_missing_qr_codes`: Generated and attached SVG QR codes for all existing confirmed bookings.

Verification command:
```bash
bench --site cinema.localhost mariadb -e "SELECT patch FROM tabPatch Log WHERE patch LIKE 'movie_tickets%';"
```
Output:
```
+--------------------------------------------------------------+
| patch                                                        |
+--------------------------------------------------------------+
| movie_tickets.patches.v1_0.recalculate_show_seat_counts      |
| movie_tickets.patches.v1_0.set_movie_slugs                   |
| movie_tickets.patches.v1_0.populate_booking_source           |
| movie_tickets.patches.v1_0.generate_missing_qr_codes         |
+--------------------------------------------------------------+
```

---

## Features Implemented (Section 4: Bonus Tasks)

### 1. Interactive Seat Map (Bonus 1)
- **Visual Seat Grid Component**:
  - Implemented in `ticket_booking.js` for Frappe Desk (`open_seat_selector` modal dialog) and on the Web Portal (`/movie-shows`).
  - Rows labeled alphabetically (A–Z) and columns numbered (1–N).
  - Strict high-visibility color coding:
    - **Green (`#16a34a`)**: Available for selection.
    - **Red (`#dc2626`)**: Booked / Unavailable.
    - **Yellow (`#eab308` with `#000000` text)**: Selected.
  - Interactive click toggling updates the `Ticket Booking` child table (`Booked Seat`) and automatically calculates total ticket amounts in real-time.

### 2. QR Code Ticket (Bonus 2)
- **Automatic SVG Generation & Attachment**:
  - Generated on booking confirmation using `pyqrcode` (`ticket_booking.py`).
  - Stored as an attached Frappe `File` record linked directly to the `qr_code` field on `Ticket Booking`.
  - Encodes structured JSON data: Booking ID, Movie Title, Theater, Screen, Show Date, Start Time, Seats, Total Amount, and Customer.
  - Embedded in booking confirmation emails (`send_booking_confirmation` and `ticket_booking_on_submit`).
  - Supported by migration patch `generate_missing_qr_codes` for retroactive generation.

### 3. Cinema Analytics Dashboard Page (Bonus 3)
- **Custom Desk Page Route**: `/app/cinema-dashboard`
- **Path**: `movie_tickets/movie_tickets/page/cinema_dashboard/`
- **Key Performance Indicators (KPI Cards)**:
  - Total Revenue (₹)
  - Today's Revenue (₹)
  - Total Confirmed Bookings
  - Total Available Seats Across All Theaters
- **Interactive Frappe Charts**:
  - **Today's Occupancy by Theater**: Bar chart (`#3b82f6`) showing percentage occupancy per theater today.
  - **30-Day Revenue Trend**: Line chart (`#10b981`) tracking daily confirmed ticket revenue over the past 30 days.
  - **Bookings by Time Slot**: Histogram/bar chart (`#f59e0b`) showing volume across Morning (09-12), Matinee (12-16), Evening (16-20), and Night (20-24).
  - **Top 5 Movies by Bookings**: Donut chart (`#6366f1`, `#ec4899`, etc.) showing share of bookings.

### 4. Custom Cinema Movie Ticket Print Format (Bonus 4)
- **Print Format Name**: `Cinema Movie Ticket` (Default print format for `Ticket Booking`)
- **Path**: `movie_tickets/movie_tickets/print_format/cinema_movie_ticket/`
- **Features**:
  - Cinema-themed dark aesthetic (`#0f172a` body, `#1e293b` card) with gold/amber branding.
  - Perforated tear-off stub line with circular cutout notches.
  - Displays movie title, poster image, theater, screen & screen type, show date/time, customer name, and individual seat pills.
  - Right stub features scan QR code image, booking ID, and gate entry instructions.
  - Includes `@media print` rules for clean, contrast-accurate paper printing and PDF generation.

### 5. Bulk Show Creator (Bonus 5)
- **API Method**: `movie_tickets.api.bulk_create_shows`
- **Background Processing**: Runs asynchronously via `frappe.enqueue("movie_tickets.api._bulk_create_shows_job", queue="default")`.
- **Desk UI Action**:
  - Added inner button `"Bulk Create Shows 🎬"` on the **Show** List view.
  - Opens an interactive modal dialog accepting Movie, MultiCheck list of Screens, From Date, To Date, comma-separated Show Times (e.g. `10:00, 14:00, 18:00, 21:30`), and optional ticket price override.
  - Built-in conflict detection: Skips overlapping time slots on the same screen without aborting other valid show creations in the batch.
  - Real-time alert notifications upon completion.

---

## How to Add Movie Posters
Movie posters are linked via the `poster` field on the `Movie` DocType (stored as a public file URL like `/files/the_dark_knight.jpg`):

1. **Via Frappe Desk**:
   - Go to **Desk > Movie Tickets > Movie**.
   - Open any Movie (e.g. `The Dark Knight`).
   - In the **Poster Image** field (Attach Image), click **Attach** or drag & drop the image file.
   - Click **Save**.
   - The poster will immediately appear in Desk and on the Web Portal (`/now-showing` and `/movie-shows`).

2. **Via Data Import Tool / Excel**:
   - Upload the poster image files to Desk via **File Manager** (under `/files/`).
   - In your Excel / CSV import template, fill the `poster` column with `/files/<filename>.jpg`.

---

## Running Test Suite

All 17 integration unit tests pass cleanly:
```bash
bench --site cinema.localhost run-tests --app movie_tickets
```

### Tests Covered:
1. `test_auto_expire_unpaid_bookings`: Background job auto-expiration of unpaid bookings and seat restoration.
2. `test_booking_decreases_available_seats`: Booking decreases available seats on Show.
3. `test_box_office_collection_report`: Execution and data structure of Box Office Collection Report.
4. `test_cancel_restores_seats`: Cancelling booking restores available seats.
5. `test_cannot_book_already_taken_seat`: Double booking prevention on same seat/show.
6. `test_cannot_book_for_cancelled_show`: Validation blocking booking on cancelled shows.
7. `test_custom_get_count_override`: Method override for `frappe.client.get_count`.
8. `test_full_refund_on_early_cancellation`: 100% refund for > 4 hours prior.
9. `test_max_seats_per_booking_limit`: Validation enforcing max seat limit.
10. `test_no_refund_on_very_late_cancellation`: 0% refund for < 2 hours prior.
11. `test_partial_refund_on_late_cancellation`: 50% refund for 2-4 hours prior.
12. `test_show_conflict_validation`: Screen time overlap conflict prevention.
13. `test_section4_interactive_seat_availability`: 2D matrix seat availability API for interactive seat map.
14. `test_section4_qr_code_generation`: Automatic SVG QR code generation and File doc attachment.
15. `test_section4_cinema_dashboard_data`: Custom Desk page KPI aggregation and Frappe Charts dataset API.
16. `test_section4_cinema_ticket_print_format`: Jinja HTML cinema ticket print format rendering.
17. `test_section4_bulk_show_creator`: Bulk show creation via background queue with time conflict skipping.
