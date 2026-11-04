# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def ticket_booking_after_insert(doc, method=None):
	"""Send email to customer:
	'Your booking {booking_name} for {movie_title} received. Complete payment within {expiry_minutes} minutes.'
	"""
	if not doc.customer_email:
		return

	expiry_mins = frappe.db.get_single_value("Booking Configuration", "booking_expiry_minutes") or 15
	subject = f"Booking Received: {doc.name} for {doc.movie_title}"
	message = f"""
	<div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
		<h3 style="color: #2b6cb0;">🎬 Booking Received</h3>
		<p>Dear {doc.customer_name or 'Customer'},</p>
		<p>Your booking <strong>{doc.name}</strong> for <strong>{doc.movie_title}</strong> has been received.</p>
		<p>Please complete your payment within <strong>{expiry_mins} minutes</strong> to secure your reservation.</p>
		<p><strong>Total Amount:</strong> ₹{float(doc.total_amount or 0):,.2f}</p>
		<p style="font-size: 13px; color: #718096;">Thank you for booking with us!</p>
	</div>
	"""
	try:
		frappe.sendmail(
			recipients=[doc.customer_email],
			subject=subject,
			message=message,
			delayed=True,
		)
	except Exception as e:
		frappe.logger("movie_tickets").warning(f"Could not send after_insert email for {doc.name}: {e}")


def ticket_booking_on_submit(doc, method=None):
	"""Send confirmation email with full details (movie, theater, screen, seats, amount, time)."""
	if not doc.customer_email:
		return

	seats_list = (
		", ".join([s.seat_label for s in doc.seats])
		if getattr(doc, "seats", None)
		else str(doc.number_of_seats or "")
	)
	subject = f"Booking Confirmation: {doc.name} - {doc.movie_title}"
	message = f"""
	<div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
		<h2 style="color: #276749;">🎉 Booking Confirmed!</h2>
		<p>Dear {doc.customer_name or 'Customer'},</p>
		<p>Your ticket booking is confirmed. Here are your booking details:</p>
		<ul>
			<li><strong>Booking ID:</strong> {doc.name}</li>
			<li><strong>Movie:</strong> {doc.movie_title}</li>
			<li><strong>Theater:</strong> {doc.theater}</li>
			<li><strong>Screen:</strong> {doc.screen}</li>
			<li><strong>Date & Time:</strong> {doc.show_date} at {doc.start_time}</li>
			<li><strong>Seats:</strong> {seats_list}</li>
			<li><strong>Amount Paid:</strong> ₹{float(doc.total_amount or 0):,.2f}</li>
		</ul>
		<p style="color: #2b6cb0; font-weight: bold;">Enjoy your movie experience!</p>
	</div>
	"""
	try:
		frappe.sendmail(
			recipients=[doc.customer_email],
			subject=subject,
			message=message,
			delayed=True,
		)
	except Exception as e:
		frappe.logger("movie_tickets").warning(f"Could not send on_submit email for {doc.name}: {e}")


def movie_before_save(doc, method=None):
	"""Auto-generate slug, update movie_status based on dates."""
	doc.generate_slug()
	doc.set_movie_status()
