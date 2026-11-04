# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Recalculate booked_seats and available_seats for all Shows by counting actual Confirmed bookings."""
	frappe.reload_doc("movie_tickets", "doctype", "show")
	frappe.reload_doc("movie_tickets", "doctype", "ticket_booking")
	frappe.reload_doc("movie_tickets", "doctype", "booked_seat")

	shows = frappe.db.sql(
		"""
		SELECT name, screen, total_seats
		FROM `tabShow`
		""",
		as_dict=True,
	)

	for s in shows:
		# Count seats in Confirmed bookings (docstatus = 1)
		count_res = frappe.db.sql(
			"""
			SELECT COUNT(bs.name) AS booked_count
			FROM `tabBooked Seat` bs
			JOIN `tabTicket Booking` tb ON tb.name = bs.parent
			WHERE tb.show = %s
			  AND tb.booking_status = 'Confirmed'
			  AND tb.docstatus = 1
			""",
			(s.name,),
			as_dict=True,
		)

		booked_count = count_res[0].booked_count if count_res else 0
		total = s.total_seats or 0
		available = max(0, total - booked_count)

		frappe.db.sql(
			"""
			UPDATE `tabShow`
			SET booked_seats = %s, available_seats = %s
			WHERE name = %s
			""",
			(booked_count, available, s.name),
		)

	frappe.db.commit()
