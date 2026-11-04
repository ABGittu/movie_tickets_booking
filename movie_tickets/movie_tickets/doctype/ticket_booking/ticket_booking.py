# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

from datetime import datetime
import re
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, now_datetime, today, to_timedelta


class TicketBooking(Document):
	def validate(self):
		self.set_show_details()
		self.validate_show_status()
		self.validate_booking_open_window()
		self.validate_seats_count()
		self.validate_duplicate_seats()
		self.validate_seat_format_and_screen_bounds()
		self.calculate_totals()
		self.validate_seat_availability()
		if not self.booking_time:
			self.booking_time = now_datetime()

	def on_submit(self):
		"""
		On submit:
		• Set booking_status to Confirmed and payment_status to Paid.
		• Update Show: increment booked_seats, decrement available_seats.
		• Generate QR code containing booking details and attach to document.
		"""
		self.db_set("booking_status", "Confirmed")
		self.db_set("payment_status", "Paid")
		self.booking_status = "Confirmed"
		self.payment_status = "Paid"

		self.update_show_seats(increment_booked=True)
		self.generate_and_attach_qr_code()

	def generate_and_attach_qr_code(self):
		"""Bonus Task 4.2: Generate a QR code containing booking details, attach to record, and return URL."""
		try:
			import io
			import pyqrcode

			seats_str = (
				", ".join([s.seat_label for s in self.seats])
				if getattr(self, "seats", None)
				else str(self.number_of_seats or "")
			)
			qr_payload = (
				f"CINEMA TICKET\n"
				f"Booking ID: {self.name}\n"
				f"Movie: {self.movie_title}\n"
				f"Theater: {self.theater}\n"
				f"Screen: {self.screen}\n"
				f"Date: {self.show_date} {self.start_time}\n"
				f"Seats: {seats_str}\n"
				f"Amount: Rs. {float(self.total_amount or 0):,.2f}\n"
				f"Customer: {self.customer_name or ''}\n"
				f"Status: Confirmed"
			)

			qr = pyqrcode.create(qr_payload, error="M")
			buffer = io.BytesIO()
			qr.svg(buffer, scale=5, background="#ffffff")
			svg_content = buffer.getvalue()

			file_name = f"qr_{self.name.replace('-', '_')}.svg"

			# Delete existing file record if regenerating
			existing_files = frappe.get_all(
				"File",
				filters={
					"attached_to_doctype": "Ticket Booking",
					"attached_to_name": self.name,
					"file_name": file_name,
				},
				pluck="name",
			)
			for ef in existing_files:
				frappe.delete_doc("File", ef, ignore_permissions=True)

			file_doc = frappe.get_doc({
				"doctype": "File",
				"file_name": file_name,
				"attached_to_doctype": "Ticket Booking",
				"attached_to_name": self.name,
				"attached_to_field": "qr_code",
				"content": svg_content,
				"is_private": 0,
			})
			file_doc.insert(ignore_permissions=True)

			self.db_set("qr_code", file_doc.file_url)
			self.qr_code = file_doc.file_url
			return file_doc.file_url
		except Exception as e:
			frappe.logger("movie_tickets").warning(
				f"Could not generate QR code for {self.name}: {e}"
			)
			return None

	def on_cancel(self):
		"""
		On cancel:
		• Set booking_status to Cancelled.
		• Calculate refund based on cancellation window:
		  >4 hours before show → 100% refund,
		  2–4 hours → 50% refund,
		  <2 hours → no refund.
		  Set refund_amount and payment_status accordingly.
		• Update Show: decrement booked_seats, increment available_seats.
		• Set cancellation_time to now_datetime().
		"""
		self.db_set("booking_status", "Cancelled")
		self.booking_status = "Cancelled"

		c_time = now_datetime()
		self.db_set("cancellation_time", c_time)
		self.cancellation_time = c_time

		self.calculate_cancellation_refund(c_time)
		self.update_show_seats(increment_booked=False)

	def set_show_details(self):
		"""Populate header details from Show if not already set."""
		if not self.show:
			return

		show_data = frappe.db.get_value(
			"Show",
			self.show,
			["movie_title", "theater", "screen", "show_date", "start_time", "ticket_price"],
			as_dict=True,
		)
		if show_data:
			if not self.movie_title:
				self.movie_title = show_data.movie_title
			if not self.theater:
				self.theater = show_data.theater
			if not self.screen:
				self.screen = show_data.screen
			if not self.show_date:
				self.show_date = show_data.show_date
			if not self.start_time:
				self.start_time = show_data.start_time
			if not self.price_per_seat:
				self.price_per_seat = show_data.ticket_price

	def validate_show_status(self):
		"""Check that the show's show_status is Scheduled or Now Playing."""
		if not self.show:
			return

		show_status = frappe.db.get_value("Show", self.show, "show_status")
		if show_status not in ["Scheduled", "Now Playing"]:
			frappe.throw(_("Cannot book tickets for a {0} show.").format(show_status))

	def validate_booking_open_window(self):
		"""Validate if show is open for booking according to booking_open_days_before."""
		if self.flags.ignore_open_window:
			return
		if not self.show_date:
			return

		open_days = frappe.db.get_single_value("Booking Configuration", "booking_open_days_before") or 7
		max_allowed_date = add_days(today(), open_days)
		if getdate(self.show_date) > getdate(max_allowed_date):
			frappe.throw(_("Bookings for this show are not open yet. Open up to {0} days in advance.").format(open_days))

	def validate_seats_count(self):
		"""Validate number_of_seats >= 1 and <= max_seats_per_booking (default 10)."""
		seat_count = len(self.seats or [])
		self.number_of_seats = seat_count

		max_seats = frappe.db.get_single_value("Booking Configuration", "max_seats_per_booking") or 10
		if seat_count < 1 or seat_count > max_seats:
			frappe.throw(_("Number of seats must be between 1 and {0} (max {0} tickets per booking).").format(max_seats))

	def validate_duplicate_seats(self):
		"""Validate no duplicate seats within the same booking."""
		seen = set()
		for seat in self.seats:
			label = (seat.seat_label or "").strip().upper()
			if not label:
				continue
			if label in seen:
				frappe.throw(_("Duplicate seat {0} in the same booking.").format(label))
			seen.add(label)

	def validate_seat_format_and_screen_bounds(self):
		"""
		Validate seat_label format: "{ROW_LETTER}-{SEAT_NUMBER}" (e.g., "A-12").
		Row letter must be within screen's seat_rows range, seat number within seats_per_row.
		"""
		if not self.screen:
			if self.show:
				self.screen = frappe.db.get_value("Show", self.show, "screen")

		screen_info = frappe.db.get_value("Screen", self.screen, ["seat_rows", "seats_per_row"], as_dict=True)
		if not screen_info:
			return

		seat_rows = screen_info.seat_rows or 0
		seats_per_row = screen_info.seats_per_row or 0
		max_row_letter = chr(ord("A") + seat_rows - 1) if seat_rows > 0 else "A"

		pattern = re.compile(r"^([A-Z])-(\d+)$")

		for seat in self.seats:
			label = (seat.seat_label or "").strip().upper()
			match = pattern.match(label)
			if not match:
				frappe.throw(_("Invalid seat label '{0}'. Must follow format 'A-12'.").format(label))

			row_letter = match.group(1)
			seat_number = int(match.group(2))

			if row_letter < "A" or row_letter > max_row_letter:
				frappe.throw(
					_("Row letter '{0}' exceeds screen row range (A-{1}).").format(row_letter, max_row_letter)
				)

			if seat_number < 1 or seat_number > seats_per_row:
				frappe.throw(
					_("Seat number {0} exceeds screen seats per row (1-{1}).").format(seat_number, seats_per_row)
				)

			seat.seat_label = f"{row_letter}-{seat_number}"
			seat.row_letter = row_letter
			seat.seat_number = seat_number
			if not seat.seat_price:
				seat.seat_price = self.price_per_seat or 0

	def calculate_totals(self):
		"""Auto-calculate number_of_seats and total_amount = number_of_seats * price_per_seat."""
		self.number_of_seats = len(self.seats or [])
		price = self.price_per_seat or 0
		self.total_amount = self.number_of_seats * price

	def validate_seat_availability(self):
		"""
		Validate each seat in the child table is available by querying
		existing confirmed/pending bookings for the same show.
		If any seat is taken, throw: "Seat {seat_label} is already booked for this show."
		"""
		if not self.show or not self.seats:
			return

		# Acquire exclusive row lock on Show to prevent concurrent race condition double-bookings
		frappe.db.sql("SELECT name FROM `tabShow` WHERE name = %s FOR UPDATE", (self.show,))

		booked_seats = frappe.db.sql(
			"""
			SELECT bs.seat_label
			FROM `tabBooked Seat` bs
			JOIN `tabTicket Booking` tb ON tb.name = bs.parent
			WHERE tb.show = %s
			  AND tb.booking_status IN ('Pending', 'Confirmed')
			  AND tb.docstatus < 2
			  AND tb.name != %s
			""",
			(self.show, self.name or ""),
			pluck="seat_label",
		)
		booked_set = set(booked_seats)

		for seat in self.seats:
			if seat.seat_label in booked_set:
				frappe.throw(_("Seat {0} is already booked for this show.").format(seat.seat_label))

	def update_show_seats(self, increment_booked=True):
		"""Update Show booked_seats and available_seats."""
		if not self.show:
			return

		show_doc = frappe.get_doc("Show", self.show)
		seats_cnt = self.number_of_seats or 0

		if increment_booked:
			show_doc.booked_seats = (show_doc.booked_seats or 0) + seats_cnt
			show_doc.available_seats = max(0, (show_doc.available_seats or 0) - seats_cnt)
		else:
			show_doc.booked_seats = max(0, (show_doc.booked_seats or 0) - seats_cnt)
			show_doc.available_seats = min(
				show_doc.total_seats or (show_doc.available_seats + seats_cnt),
				(show_doc.available_seats or 0) + seats_cnt,
			)

		show_doc.flags.ignore_validate = True
		show_doc.flags.ignore_permissions = True
		show_doc.save()

	def calculate_cancellation_refund(self, c_time):
		"""
		Calculate refund based on cancellation window:
		>4 hours before show → 100% refund,
		2–4 hours → 50% refund,
		<2 hours → no refund.
		Set refund_amount and payment_status accordingly.
		"""
		if self.cancellation_reason == "Show Cancelled":
			refund = self.total_amount or 0.0
		else:
			show_doc = frappe.get_doc("Show", self.show)
			s_date = getdate(show_doc.show_date)
			s_time_td = to_timedelta(show_doc.start_time)
			show_dt = datetime.combine(s_date, datetime.min.time()) + s_time_td

			hours_diff = (show_dt - c_time).total_seconds() / 3600.0

			full_refund_hours = frappe.db.get_single_value("Booking Configuration", "full_refund_hours")
			if full_refund_hours is None:
				full_refund_hours = 4.0
			partial_refund_hours = frappe.db.get_single_value("Booking Configuration", "partial_refund_hours")
			if partial_refund_hours is None:
				partial_refund_hours = 2.0
			partial_refund_pct = frappe.db.get_single_value("Booking Configuration", "partial_refund_pct")
			if partial_refund_pct is None:
				partial_refund_pct = 50.0

			if hours_diff > full_refund_hours:
				refund = float(self.total_amount or 0.0)
			elif hours_diff >= partial_refund_hours:
				refund = float(self.total_amount or 0.0) * (float(partial_refund_pct) / 100.0)
			else:
				refund = 0.0

		self.refund_amount = refund
		self.db_set("refund_amount", refund)

		if refund > 0:
			self.db_set("payment_status", "Refunded")
			self.payment_status = "Refunded"


def has_permission(doc, ptype="read", user=None, debug=False):
	"""Customers see only bookings where booked_by = current user."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True

	roles = frappe.get_roles(user)
	if "System Manager" in roles or "Cinema Manager" in roles or "Box Office Staff" in roles:
		return True

	if "Customer" in roles:
		if getattr(doc, "booked_by", None) == user or getattr(doc, "owner", None) == user:
			return True
		return False

	return True


def get_permission_query_conditions(user=None):
	"""Customers see only bookings where booked_by = current user."""
	user = user or frappe.session.user
	if user == "Administrator":
		return ""

	roles = frappe.get_roles(user)
	if "System Manager" in roles or "Cinema Manager" in roles or "Box Office Staff" in roles:
		return ""

	if "Customer" in roles:
		return f"(`tabTicket Booking`.`booked_by` = {frappe.db.escape(user)} OR `tabTicket Booking`.`owner` = {frappe.db.escape(user)})"

	return ""

