# Copyright (c) 2026, Abhijit P Dodiya and Contributors
# See license.txt

from datetime import datetime, timedelta
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, now_datetime, today


class IntegrationTestTicketBooking(IntegrationTestCase):
	def setUp(self):
		frappe.db.rollback()
		self.ensure_test_prerequisites()

	def tearDown(self):
		frappe.db.rollback()

	def ensure_test_prerequisites(self):
		# Ensure Genre
		if not frappe.db.exists("Movie Genre", "Action"):
			g = frappe.new_doc("Movie Genre")
			g.genre_name = "Action"
			g.insert()

		# Ensure Theater
		if not frappe.db.exists("Theater", "Test Theater"):
			t = frappe.new_doc("Theater")
			t.theater_name = "Test Theater"
			t.city = "Ahmedabad"
			t.address = "Test Road"
			t.insert()

		# Ensure Screen with 100 seats (10x10)
		screen_name = "Test Theater-Screen 1"
		if not frappe.db.exists("Screen", screen_name):
			s = frappe.new_doc("Screen")
			s.screen_name = "Screen 1"
			s.theater = "Test Theater"
			s.screen_type = "Standard"
			s.seat_rows = 10
			s.seats_per_row = 10
			s.total_seats = 100
			s.base_price = 200.0
			s.insert()

		# Ensure Movie
		if not frappe.db.exists("Movie", {"title": "Test Movie"}):
			m = frappe.new_doc("Movie")
			m.title = "Test Movie"
			m.language = "English"
			m.genre = "Action"
			m.duration_minutes = 120
			m.release_date = today()
			m.insert()

		# Ensure Booking Configuration
		conf = frappe.get_single("Booking Configuration")
		conf.max_seats_per_booking = 10
		conf.booking_expiry_minutes = 15
		conf.full_refund_hours = 4.0
		conf.partial_refund_hours = 2.0
		conf.partial_refund_pct = 50.0
		conf.enable_auto_expiry = 1
		conf.booking_open_days_before = 7
		conf.save()

	def create_show(self, show_date=None, start_time="10:00:00", end_time=None, movie=None, screen="Test Theater-Screen 1"):
		movie_name = movie or frappe.db.get_value("Movie", {"title": "Test Movie"}, "name")
		sh = frappe.new_doc("Show")
		sh.movie = movie_name
		sh.screen = screen
		sh.show_date = show_date or today()
		sh.start_time = start_time
		if end_time:
			sh.end_time = end_time
		sh.ticket_price = 200.0
		sh.show_status = "Scheduled"
		sh.flags.ignore_date_validation = True
		sh.flags.ignore_movie_status_validation = True
		sh.insert()
		return sh

	def create_booking(self, show_name, seats, customer_name="Test Customer", email="test@example.com"):
		bkg = frappe.new_doc("Ticket Booking")
		bkg.show = show_name
		bkg.customer_name = customer_name
		bkg.customer_email = email
		bkg.customer_phone = "9876543210"
		bkg.flags.ignore_open_window = True
		for s in seats:
			parts = s.split("-")
			bkg.append("seats", {
				"seat_label": s,
				"row_letter": parts[0],
				"seat_number": int(parts[1])
			})
		bkg.insert()
		return bkg

	def test_booking_decreases_available_seats(self):
		"""Create a show with 100 seats. Book 3 seats. Assert available_seats = 97, booked_seats = 3."""
		show = self.create_show(start_time="09:00:00")
		self.assertEqual(show.total_seats, 100)
		self.assertEqual(show.available_seats, 100)

		bkg = self.create_booking(show.name, ["A-1", "A-2", "A-3"])
		bkg.submit()

		show.reload()
		self.assertEqual(show.available_seats, 97)
		self.assertEqual(show.booked_seats, 3)

	def test_cannot_book_already_taken_seat(self):
		"""Book seat A-1. Attempt another booking with A-1 for same show. Assert frappe.ValidationError."""
		show = self.create_show(start_time="12:00:00")
		bkg1 = self.create_booking(show.name, ["A-1"], email="user1@example.com")
		bkg1.submit()

		with self.assertRaises(frappe.ValidationError):
			bkg2 = self.create_booking(show.name, ["A-1"], email="user2@example.com")

	def test_cannot_book_for_cancelled_show(self):
		"""Cancel a show. Attempt booking. Assert error about show status."""
		show = self.create_show(start_time="15:00:00")
		show.show_status = "Cancelled"
		show.save()

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(show.name, ["A-1"])

	def test_max_seats_per_booking_limit(self):
		"""Book 11 seats in one booking (exceeds max 10). Assert validation error."""
		show = self.create_show(start_time="18:00:00")
		seats_11 = [f"A-{i}" for i in range(1, 11)] + ["B-1"]

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(show.name, seats_11)

	def test_full_refund_on_early_cancellation(self):
		"""Book for a show 6 hours away. Cancel. Assert refund_amount = total_amount."""
		future_time = (now_datetime() + timedelta(hours=6, minutes=30)).time()
		show = self.create_show(show_date=today(), start_time=future_time.strftime("%H:%M:%S"))

		bkg = self.create_booking(show.name, ["A-1", "A-2"])
		bkg.submit()
		self.assertEqual(bkg.total_amount, 400.0)

		bkg.cancel()
		bkg.reload()
		self.assertEqual(bkg.refund_amount, 400.0)
		self.assertEqual(bkg.payment_status, "Refunded")

	def test_partial_refund_on_late_cancellation(self):
		"""Book for a show 3 hours away. Cancel. Assert refund_amount = 50% of total_amount."""
		future_time = (now_datetime() + timedelta(hours=3, minutes=10)).time()
		show = self.create_show(show_date=today(), start_time=future_time.strftime("%H:%M:%S"))

		bkg = self.create_booking(show.name, ["A-1", "A-2"])
		bkg.submit()
		self.assertEqual(bkg.total_amount, 400.0)

		bkg.cancel()
		bkg.reload()
		self.assertEqual(bkg.refund_amount, 200.0)
		self.assertEqual(bkg.payment_status, "Refunded")

	def test_no_refund_on_very_late_cancellation(self):
		"""Book for a show 1 hour away. Cancel. Assert refund_amount = 0."""
		future_time = (now_datetime() + timedelta(hours=1, minutes=5)).time()
		show = self.create_show(show_date=today(), start_time=future_time.strftime("%H:%M:%S"))

		bkg = self.create_booking(show.name, ["A-1", "A-2"])
		bkg.submit()
		self.assertEqual(bkg.total_amount, 400.0)

		bkg.cancel()
		bkg.reload()
		self.assertEqual(bkg.refund_amount, 0.0)

	def test_show_conflict_validation(self):
		"""Create show on Screen 1 at 14:00-16:30. Create overlapping show 15:00-17:00 on same screen/date. Assert error."""
		conflict_date = add_days(today(), 2)
		show1 = self.create_show(show_date=conflict_date, start_time="14:00:00")
		show1.end_time = "16:30:00"
		show1.save()

		with self.assertRaises(frappe.ValidationError):
			show2 = self.create_show(show_date=conflict_date, start_time="15:00:00")
			show2.end_time = "17:00:00"
			show2.save()

	def test_cancel_restores_seats(self):
		"""Book 4 seats, submit (confirm), then cancel. Assert available_seats restored."""
		future_time = (now_datetime() + timedelta(hours=5)).time()
		show = self.create_show(show_date=today(), start_time=future_time.strftime("%H:%M:%S"))

		bkg = self.create_booking(show.name, ["A-1", "A-2", "A-3", "A-4"])
		bkg.submit()

		show.reload()
		self.assertEqual(show.available_seats, 96)
		self.assertEqual(show.booked_seats, 4)

		bkg.cancel()

		show.reload()
		self.assertEqual(show.available_seats, 100)
		self.assertEqual(show.booked_seats, 0)

	def test_auto_expire_unpaid_bookings(self):
		"""Task 3.1: Expire unpaid pending bookings older than booking_expiry_minutes and restore seats."""
		from movie_tickets.tasks import auto_expire_unpaid_bookings

		future_time = (now_datetime() + timedelta(hours=3)).time()
		show = self.create_show(show_date=today(), start_time=future_time.strftime("%H:%M:%S"))

		bkg = self.create_booking(show.name, ["B-1", "B-2"])
		# Backdate booking_time to 30 mins ago
		old_time = now_datetime() - timedelta(minutes=30)
		bkg.db_set("booking_time", old_time)

		expired = auto_expire_unpaid_bookings()
		self.assertGreaterEqual(expired, 1)

		bkg.reload()
		self.assertEqual(bkg.booking_status, "Expired")

		show.reload()
		self.assertEqual(show.available_seats, 100)
		self.assertEqual(show.booked_seats, 0)

		# Verify that an expired booking cannot be paid
		from movie_tickets.api import confirm_payment
		with self.assertRaises(frappe.ValidationError):
			confirm_payment(bkg.name)

	def test_box_office_collection_report(self):
		"""Task 3.3: Execute Box Office Collection Report and assert structure."""
		from movie_tickets.movie_tickets.report.box_office_collection_report.box_office_collection_report import execute

		columns, data, message, chart, summary = execute()
		self.assertTrue(len(columns) >= 9)
		self.assertIsNotNone(chart)
		self.assertEqual(chart.get("type"), "bar")
		self.assertTrue(len(summary) >= 4)

	def test_custom_get_count_override(self):
		"""Task 3.2: Verify custom_get_count override works."""
		from movie_tickets.overrides import custom_get_count

		count = custom_get_count("Movie")
		self.assertIsInstance(count, int)
		self.assertGreaterEqual(count, 1)

	def test_section4_interactive_seat_availability(self):
		"""Bonus 1: Test seat availability API for interactive seat map."""
		from movie_tickets.api import get_seat_availability

		show = self.create_show(show_date=today(), start_time="11:00:00")
		bkg = self.create_booking(show.name, ["A-1", "A-2"])

		res = get_seat_availability(show.name)
		self.assertEqual(res["total_rows"], 10)
		self.assertEqual(res["seats_per_row"], 10)

		# Flatten grid and find A-1 and A-2
		seats = [s for row in res["seat_grid"] for s in row]
		a1 = next(s for s in seats if s["seat_label"] == "A-1")
		a3 = next(s for s in seats if s["seat_label"] == "A-3")
		self.assertEqual(a1["status"], "booked")
		self.assertEqual(a3["status"], "available")

	def test_section4_qr_code_generation(self):
		"""Bonus 2: Test QR code generation and attachment on ticket booking confirmation."""
		from movie_tickets.api import get_booking_qr_details

		show = self.create_show(show_date=today(), start_time="12:00:00")
		bkg = self.create_booking(show.name, ["C-1", "C-2"])
		bkg.submit()

		bkg.reload()
		self.assertTrue(bool(bkg.qr_code))
		self.assertTrue(bkg.qr_code.endswith(".svg"))

		# Check File doc exists
		file_exists = frappe.db.exists("File", {"file_url": bkg.qr_code})
		self.assertTrue(bool(file_exists))

		# Check get_booking_qr_details returns data for the dialog
		qr_details = get_booking_qr_details(bkg.name)
		self.assertTrue(qr_details["success"])
		self.assertEqual(qr_details["booking_name"], bkg.name)
		self.assertEqual(qr_details["qr_code"], bkg.qr_code)
		self.assertEqual(qr_details["seats"], "C-1, C-2")

	def test_section4_cinema_dashboard_data(self):
		"""Bonus 3: Test custom cinema dashboard data API."""
		from movie_tickets.movie_tickets.page.cinema_dashboard.cinema_dashboard import get_dashboard_data

		data = get_dashboard_data()
		self.assertIn("kpis", data)
		self.assertIn("chart_occupancy", data)
		self.assertIn("chart_revenue_trend", data)
		self.assertIn("chart_time_slots", data)
		self.assertIn("chart_top_movies", data)

		self.assertGreaterEqual(data["kpis"]["total_seats"], 0)
		self.assertEqual(data["chart_revenue_trend"]["type"], "line")
		self.assertEqual(data["chart_time_slots"]["type"], "bar")
		self.assertEqual(data["chart_top_movies"]["type"], "donut")

	def test_section4_cinema_ticket_print_format(self):
		"""Bonus 4: Test Cinema Movie Ticket print format rendering."""
		show = self.create_show(show_date=today(), start_time="13:00:00")
		bkg = self.create_booking(show.name, ["D-1", "D-2"])
		bkg.submit()

		html = frappe.get_print("Ticket Booking", bkg.name, "Cinema Movie Ticket")
		self.assertIn("CINEMA ENTRY", html)
		self.assertIn("Test Movie", html)
		self.assertIn("D-1", html)
		self.assertIn("D-2", html)
		self.assertIn(bkg.name, html)

	def test_section4_bulk_show_creator(self):
		"""Bonus 5: Test bulk show creation API and conflict handling."""
		from movie_tickets.api import bulk_create_shows

		movie_name = frappe.db.get_value("Movie", {"title": "Test Movie"}, "name")
		screen_name = "Test Theater-Screen 1"
		target_date = add_days(today(), 45)

		# Clean any pre-existing shows on this test target date
		frappe.db.delete("Show", {"screen": screen_name, "show_date": str(target_date)})
		frappe.db.commit()

		# Schedule for a future date
		res = bulk_create_shows(
			movie=movie_name,
			screens=[screen_name],
			from_date=str(target_date),
			to_date=str(target_date),
			show_times=["08:00:00", "11:30:00"],
			ticket_price=180.0,
			queue_now=True,
		)
		self.assertTrue(res["success"])
		self.assertEqual(res["created_count"], 2)

		# Calling again should gracefully detect conflicts and skip
		res_dup = bulk_create_shows(
			movie=movie_name,
			screens=[screen_name],
			from_date=str(target_date),
			to_date=str(target_date),
			show_times=["08:00:00", "11:30:00"],
			ticket_price=180.0,
			queue_now=True,
		)
		self.assertTrue(res_dup["success"])
		self.assertEqual(res_dup["created_count"], 0)
		self.assertEqual(res_dup["skipped_count"], 2)

		# Cleanup test shows
		frappe.db.delete("Show", {"screen": screen_name, "show_date": str(target_date)})
		frappe.db.commit()

