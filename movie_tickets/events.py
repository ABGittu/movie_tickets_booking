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
		<p>Dear {doc.customer_name or "Customer"},</p>
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
	if not doc.qr_code and hasattr(doc, "generate_and_attach_qr_code"):
		doc.generate_and_attach_qr_code()

	qr_section = ""
	if doc.qr_code:
		qr_url = frappe.utils.get_url(doc.qr_code)
		qr_section = f"""
		<div style="text-align: center; margin: 20px 0; padding: 15px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px;">
			<div style="font-size: 11px; font-weight: 700; color: #475569; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px;">
				DIGITAL ENTRY QR CODE
			</div>
			<img src="{qr_url}" alt="Ticket QR Code" width="150" height="150" style="background: #ffffff; padding: 6px; border: 1px solid #e2e8f0; border-radius: 6px;" />
			<div style="font-size: 11px; color: #64748b; margin-top: 6px;">
				Present this QR code or Booking ID at the screen entrance
			</div>
		</div>
		"""

	subject = f"Booking Confirmation: {doc.name} - {doc.movie_title}"
	message = f"""
	<div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; max-width: 550px;">
		<h2 style="color: #276749; margin-top: 0;">🎉 Booking Confirmed!</h2>
		<p>Dear {doc.customer_name or "Customer"},</p>
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
		{qr_section}
		<p style="color: #2b6cb0; font-weight: bold; text-align: center;">Enjoy your movie experience!</p>
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
