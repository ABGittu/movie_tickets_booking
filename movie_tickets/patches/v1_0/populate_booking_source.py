# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Set booking_source = 'Counter' for all existing bookings where booking_source is NULL or empty."""
	frappe.reload_doc("movie_tickets", "doctype", "ticket_booking")

	frappe.db.sql(
		"""
		UPDATE `tabTicket Booking`
		SET booking_source = 'Counter'
		WHERE booking_source IS NULL OR booking_source = ''
		"""
	)

	frappe.db.commit()
