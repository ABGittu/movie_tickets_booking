# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today, to_timedelta


class Show(Document):
	def before_insert(self):
		self.calculate_end_time()
		self.set_default_ticket_price()
		self.initialize_seats()

	def validate(self):
		self.calculate_end_time()
		self.validate_show_date()
		self.validate_movie_status()
		self.validate_showtime_conflicts()

	def on_update(self):
		prev = self.get_doc_before_save()
		if prev and prev.show_status != "Cancelled" and self.show_status == "Cancelled":
			self.cancel_related_bookings()

	def calculate_end_time(self):
		"""Auto-calculate end_time = start_time + movie.duration_minutes using Python datetime."""
		if not self.movie or not self.start_time:
			return

		duration = frappe.db.get_value("Movie", self.movie, "duration_minutes") or 0
		if not duration:
			return

		start_td = to_timedelta(self.start_time)
		base_dt = datetime(2000, 1, 1) + start_td
		end_dt = base_dt + timedelta(minutes=duration)
		self.end_time = end_dt.strftime("%H:%M:%S")

	def set_default_ticket_price(self):
		"""Auto-set ticket_price from screen.base_price if not explicitly provided."""
		if not self.ticket_price and self.screen:
			base_price = frappe.db.get_value("Screen", self.screen, "base_price")
			if base_price:
				self.ticket_price = base_price

	def initialize_seats(self):
		"""Set available_seats = screen.total_seats on before_insert."""
		if self.screen:
			total_seats = frappe.db.get_value("Screen", self.screen, "total_seats") or 0
			self.total_seats = total_seats
			self.available_seats = total_seats
			self.booked_seats = 0

	def validate_show_date(self):
		"""Validate that show_date is not in the past (allow today)."""
		if self.flags.ignore_date_validation:
			return
		if self.show_date and getdate(self.show_date) < getdate(today()):
			frappe.throw(_("Show Date cannot be in the past."))

	def validate_movie_status(self):
		"""Validate that the movie's movie_status is not Ended."""
		if self.flags.ignore_movie_status_validation:
			return
		if not self.movie:
			return
		movie_status = frappe.db.get_value("Movie", self.movie, "movie_status")
		if movie_status == "Ended":
			frappe.throw(_("Cannot schedule a show for a movie with status 'Ended'."))

	def validate_showtime_conflicts(self):
		"""
		Check for showtime conflicts:
		No other show on the same screen should overlap with this show's time window
		(start_time to end_time) on the same show_date.
		If conflict found, throw:
		'Screen {screen} already has a show scheduled from {existing_start} to {existing_end} on {show_date}.'
		"""
		if not self.screen or not self.show_date or not self.start_time or not self.end_time:
			return

		my_start = to_timedelta(self.start_time)
		my_end = to_timedelta(self.end_time)

		existing_shows = frappe.get_all(
			"Show",
			filters={
				"screen": self.screen,
				"show_date": self.show_date,
				"show_status": ["!=", "Cancelled"],
				"name": ["!=", self.name or ""],
			},
			fields=["name", "start_time", "end_time"],
		)

		for s in existing_shows:
			ex_start = to_timedelta(s.start_time)
			ex_end = to_timedelta(s.end_time)

			# Overlap check: start1 < end2 and end1 > start2
			if my_start < ex_end and my_end > ex_start:
				frappe.throw(
					_(
						"Screen {screen} already has a show scheduled from {existing_start} to {existing_end} on {show_date}."
					).format(
						screen=self.screen,
						existing_start=str(s.start_time),
						existing_end=str(s.end_time),
						show_date=self.show_date,
					)
				)

	def cancel_related_bookings(self):
		"""
		If show_status changes to Cancelled, find all Pending/Confirmed bookings
		for this show and auto-cancel them with reason 'Show Cancelled'.
		For paid bookings, set refund_amount = total_amount and payment_status to Refunded.
		For unpaid pending bookings, set booking_status to Cancelled without refund.
		"""
		bookings = frappe.get_all(
			"Ticket Booking",
			filters={
				"show": self.name,
				"booking_status": ["in", ["Pending", "Confirmed"]],
			},
			fields=["name", "docstatus", "total_amount", "payment_status"],
		)

		for b in bookings:
			booking_doc = frappe.get_doc("Ticket Booking", b.name)
			booking_doc.cancellation_reason = "Show Cancelled"
			booking_doc.cancellation_time = frappe.utils.now_datetime()
			booking_doc.flags.ignore_permissions = True
			booking_doc.flags.ignore_validate = True

			if booking_doc.docstatus == 1:
				booking_doc.refund_amount = booking_doc.total_amount
				booking_doc.payment_status = "Refunded"
				booking_doc.cancel()
			else:
				booking_doc.booking_status = "Cancelled"
				if booking_doc.payment_status == "Paid":
					booking_doc.refund_amount = booking_doc.total_amount
					booking_doc.payment_status = "Refunded"
				else:
					booking_doc.refund_amount = 0.0
					booking_doc.payment_status = "Unpaid"
				booking_doc.save()
