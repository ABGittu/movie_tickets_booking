# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

import json
from datetime import datetime, timedelta
import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, now_datetime, to_timedelta, today


@frappe.whitelist()
def get_seat_availability(show_name):
	"""
	Returns: total rows, seats per row, and a 2D array of seat objects
	[{seat_label: "A-1", status: "available"}, {seat_label: "A-2", status: "booked"}, ...].
	Query Confirmed and Pending bookings for the show to determine booked seats.
	"""
	if not show_name:
		frappe.throw(_("show_name is required."))

	show = frappe.get_doc("Show", show_name)
	screen = frappe.get_doc("Screen", show.screen)

	seat_rows = screen.seat_rows or 0
	seats_per_row = screen.seats_per_row or 0

	# Query booked seats from Confirmed and Pending bookings (excluding cancelled/rejected)
	booked_seat_labels = frappe.db.sql(
		"""
		SELECT bs.seat_label
		FROM `tabBooked Seat` bs
		JOIN `tabTicket Booking` tb ON tb.name = bs.parent
		WHERE tb.show = %s
		  AND tb.booking_status IN ('Pending', 'Confirmed')
		  AND tb.docstatus < 2
		""",
		(show_name,),
		pluck="seat_label",
	)
	booked_set = set(booked_seat_labels or [])

	seat_grid = []
	all_seats = []

	for r in range(seat_rows):
		row_letter = chr(ord("A") + r)
		row_seats = []
		for c in range(1, seats_per_row + 1):
			seat_label = f"{row_letter}-{c}"
			status = "booked" if seat_label in booked_set else "available"
			seat_obj = {
				"seat_label": seat_label,
				"row_letter": row_letter,
				"seat_number": c,
				"status": status,
				"seat_price": show.ticket_price or screen.base_price,
			}
			row_seats.append(seat_obj)
			all_seats.append(seat_obj)
		seat_grid.append(row_seats)

	return {
		"show_name": show_name,
		"movie_title": show.movie_title,
		"theater": show.theater,
		"screen": show.screen,
		"ticket_price": show.ticket_price,
		"total_rows": seat_rows,
		"seats_per_row": seats_per_row,
		"total_seats": screen.total_seats,
		"available_seats": show.available_seats,
		"seat_grid": seat_grid,
		"seats": all_seats,
	}


@frappe.whitelist(allow_guest=False)
def create_booking(show, customer_name, customer_email, customer_phone, seats):
	"""
	Creates a Ticket Booking with specified seats.
	Re-validates seat availability server-side (using locking to prevent race conditions).
	Returns:
	{"success": True, "booking_name": "BKG-2026-00001", "total_amount": 1350, "message": "Booking created. Complete payment within 15 minutes."}
	"""
	if not show:
		frappe.throw(_("Show is required."))
	if not customer_name or not customer_email or not customer_phone:
		frappe.throw(_("Customer name, email, and phone are required."))

	if isinstance(seats, str):
		try:
			seats = json.loads(seats)
		except Exception:
			# If comma separated string
			seats = [s.strip() for s in seats.split(",") if s.strip()]

	if not seats:
		frappe.throw(_("At least one seat must be selected."))

	# Acquire database row lock on the Show to prevent race condition double-booking
	frappe.db.sql("SELECT name FROM `tabShow` WHERE name = %s FOR UPDATE", (show,))

	# Re-validate seat availability server-side under transaction lock
	booked_seats = frappe.db.sql(
		"""
		SELECT bs.seat_label
		FROM `tabBooked Seat` bs
		JOIN `tabTicket Booking` tb ON tb.name = bs.parent
		WHERE tb.show = %s
		  AND tb.booking_status IN ('Pending', 'Confirmed')
		  AND tb.docstatus < 2
		""",
		(show,),
		pluck="seat_label",
	)
	booked_set = set(booked_seats or [])

	for s_label in seats:
		if s_label in booked_set:
			frappe.throw(_("Seat {0} is already booked for this show.").format(s_label))

	# Create Ticket Booking document
	booking = frappe.new_doc("Ticket Booking")
	booking.show = show
	booking.customer_name = customer_name
	booking.customer_email = customer_email
	booking.customer_phone = customer_phone
	booking.booking_source = "Website"
	booking.booked_by = frappe.session.user
	booking.booking_time = now_datetime()

	show_doc = frappe.get_doc("Show", show)
	price = show_doc.ticket_price or 0.0

	for s_label in seats:
		parts = s_label.split("-")
		row_letter = parts[0]
		seat_num = int(parts[1]) if len(parts) > 1 else 1
		booking.append(
			"seats",
			{
				"seat_label": s_label,
				"row_letter": row_letter,
				"seat_number": seat_num,
				"seat_price": price,
			},
		)

	booking.flags.ignore_permissions = True
	booking.insert()

	return {
		"success": True,
		"booking_name": booking.name,
		"total_amount": booking.total_amount,
		"message": "Booking created. Complete payment within 15 minutes.",
	}


@frappe.whitelist(allow_guest=True)
def get_shows_for_movie(movie, city=None, date=None):
	"""
	Returns upcoming shows for a movie, optionally filtered by city and/or date.
	Includes: show_name, theater, screen, screen_type, show_date, start_time, ticket_price, available_seats.
	"""
	if not movie:
		frappe.throw(_("Movie parameter is required."))

	conditions = [
		"s.movie = %(movie)s",
		"s.show_status IN ('Scheduled', 'Now Playing')",
		"s.show_date >= %(today)s",
	]
	params = {"movie": movie, "today": today()}

	if date:
		conditions.append("s.show_date = %(date)s")
		params["date"] = date

	if city:
		conditions.append("t.city = %(city)s")
		params["city"] = city

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			s.name AS show_name,
			s.theater,
			s.screen,
			sc.screen_type,
			s.show_date,
			s.start_time,
			s.end_time,
			s.ticket_price,
			s.available_seats,
			s.total_seats,
			t.city,
			t.address AS theater_address
		FROM `tabShow` s
		JOIN `tabScreen` sc ON sc.name = s.screen
		JOIN `tabTheater` t ON t.name = s.theater
		WHERE {where_clause}
		ORDER BY s.show_date ASC, s.start_time ASC
	"""

	shows = frappe.db.sql(query, params, as_dict=True)
	return shows


@frappe.whitelist()
def send_booking_confirmation(booking_name):
	"""
	Sends formatted HTML email to customer with:
	movie, theater, screen, show time, seats, amount, booking ID.
	"""
	if not booking_name:
		frappe.throw(_("Booking name is required."))

	booking = frappe.get_doc("Ticket Booking", booking_name)
	if not booking.customer_email:
		frappe.throw(_("Customer email not found on booking."))

	seats_list = ", ".join(s.seat_label for s in (booking.seats or []))

	if not booking.qr_code and hasattr(booking, "generate_and_attach_qr_code"):
		booking.generate_and_attach_qr_code()

	qr_html = ""
	if booking.qr_code:
		qr_url = frappe.utils.get_url(booking.qr_code)
		qr_html = f"""
		<div style="text-align: center; margin: 20px 0; padding: 15px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px;">
			<div style="font-size: 11px; font-weight: 700; color: #475569; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px;">
				DIGITAL ENTRY QR CODE
			</div>
			<img src="{qr_url}" alt="Ticket QR Code" width="150" height="150" style="background: #ffffff; padding: 6px; border: 1px solid #e2e8f0; border-radius: 6px;" />
			<div style="font-size: 11px; color: #64748b; margin-top: 6px;">
				Scan at theater counter or screen entrance
			</div>
		</div>
		"""

	html_message = f"""
	<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
		<div style="text-align: center; border-bottom: 2px solid #3182ce; padding-bottom: 15px; margin-bottom: 20px;">
			<h2 style="color: #2b6cb0; margin: 0;">🎬 Movie Ticket Confirmation</h2>
			<p style="color: #718096; margin-top: 5px;">Booking ID: <strong>{booking.name}</strong></p>
		</div>

		<table style="width: 100%; border-collapse: collapse; font-size: 15px;">
			<tr>
				<td style="padding: 8px 0; color: #4a5568;"><strong>Movie:</strong></td>
				<td style="padding: 8px 0; color: #1a202c; font-weight: bold;">{booking.movie_title}</td>
			</tr>
			<tr>
				<td style="padding: 8px 0; color: #4a5568;"><strong>Theater:</strong></td>
				<td style="padding: 8px 0; color: #1a202c;">{booking.theater}</td>
			</tr>
			<tr>
				<td style="padding: 8px 0; color: #4a5568;"><strong>Screen:</strong></td>
				<td style="padding: 8px 0; color: #1a202c;">{booking.screen}</td>
			</tr>
			<tr>
				<td style="padding: 8px 0; color: #4a5568;"><strong>Date & Time:</strong></td>
				<td style="padding: 8px 0; color: #1a202c;">{booking.show_date} at {booking.start_time}</td>
			</tr>
			<tr>
				<td style="padding: 8px 0; color: #4a5568;"><strong>Seats:</strong></td>
				<td style="padding: 8px 0; color: #2b6cb0; font-weight: bold;">{seats_list} ({booking.number_of_seats} seats)</td>
			</tr>
			<tr>
				<td style="padding: 8px 0; color: #4a5568;"><strong>Total Amount:</strong></td>
				<td style="padding: 8px 0; color: #276749; font-size: 18px; font-weight: bold;">₹{booking.total_amount:,.2f}</td>
			</tr>
			<tr>
				<td style="padding: 8px 0; color: #4a5568;"><strong>Payment Status:</strong></td>
				<td style="padding: 8px 0; color: #1a202c;">{booking.payment_status}</td>
			</tr>
		</table>

		{qr_html}

		<div style="margin-top: 25px; padding: 15px; background: #edf2f7; border-radius: 6px; text-align: center; font-size: 13px; color: #4a5568;">
			Please arrive 15 minutes prior to the show time. Present this email or your Booking ID at the counter or screen entrance. Enjoy your movie!
		</div>
	</div>
	"""

	frappe.sendmail(
		recipients=[booking.customer_email],
		subject=f"Movie Booking Confirmation - {booking.name} ({booking.movie_title})",
		message=html_message,
	)

	return {
		"success": True,
		"message": f"Confirmation email sent to {booking.customer_email}",
	}


@frappe.whitelist()
def get_revenue_summary(theater=None, from_date=None, to_date=None):
	"""
	Returns: total_bookings, total_revenue, total_seats_sold, avg_occupancy_pct, top_movie by revenue.
	Uses frappe.db.sql with parameterized queries.
	"""
	conditions = ["tb.docstatus = 1"]
	params = {}

	if theater:
		conditions.append("tb.theater = %(theater)s")
		params["theater"] = theater

	if from_date:
		conditions.append("tb.show_date >= %(from_date)s")
		params["from_date"] = from_date

	if to_date:
		conditions.append("tb.show_date <= %(to_date)s")
		params["to_date"] = to_date

	where_clause = " AND ".join(conditions)

	# 1. Total bookings, total revenue, total seats sold
	stats_query = f"""
		SELECT
			COUNT(DISTINCT tb.name) AS total_bookings,
			COALESCE(SUM(tb.total_amount), 0.0) AS total_revenue,
			COALESCE(SUM(tb.number_of_seats), 0) AS total_seats_sold
		FROM `tabTicket Booking` tb
		WHERE {where_clause}
	"""
	stats = frappe.db.sql(stats_query, params, as_dict=True)[0]

	# 2. Top movie by revenue
	top_movie_query = f"""
		SELECT
			tb.movie_title,
			SUM(tb.total_amount) AS revenue
		FROM `tabTicket Booking` tb
		WHERE {where_clause}
		GROUP BY tb.movie_title
		ORDER BY revenue DESC
		LIMIT 1
	"""
	top_movie_res = frappe.db.sql(top_movie_query, params, as_dict=True)
	top_movie = top_movie_res[0].movie_title if top_movie_res else None

	# 3. Average occupancy % across shows for the filter
	show_cond = ["s.docstatus < 2"]
	show_params = {}
	if theater:
		show_cond.append("s.theater = %(theater)s")
		show_params["theater"] = theater
	if from_date:
		show_cond.append("s.show_date >= %(from_date)s")
		show_params["from_date"] = from_date
	if to_date:
		show_cond.append("s.show_date <= %(to_date)s")
		show_params["to_date"] = to_date

	show_where = " AND ".join(show_cond)
	occupancy_query = f"""
		SELECT
			AVG(CASE WHEN s.total_seats > 0 THEN (s.booked_seats / s.total_seats) * 100.0 ELSE 0.0 END) AS avg_occupancy
		FROM `tabShow` s
		WHERE {show_where}
	"""
	occupancy_res = frappe.db.sql(occupancy_query, show_params, as_dict=True)
	avg_occupancy = flt(occupancy_res[0].avg_occupancy, 2) if occupancy_res and occupancy_res[0].avg_occupancy is not None else 0.0

	return {
		"total_bookings": stats.total_bookings or 0,
		"total_revenue": flt(stats.total_revenue or 0.0, 2),
		"total_seats_sold": stats.total_seats_sold or 0,
		"avg_occupancy_pct": avg_occupancy,
		"top_movie": top_movie,
	}


@frappe.whitelist()
def confirm_payment(booking_name):
	"""
	Submits a Ticket Booking, transitioning from Pending/Unpaid to Confirmed/Paid.
	Sends confirmation email to customer.
	"""
	if not booking_name:
		frappe.throw(_("Booking name is required."))

	booking = frappe.get_doc("Ticket Booking", booking_name)
	user = frappe.session.user

	if user != "Administrator" and "System Manager" not in frappe.get_roles(user) and "Cinema Manager" not in frappe.get_roles(user):
		if booking.booked_by != user and booking.owner != user:
			frappe.throw(_("You are not authorized to confirm payment for this booking."))

	if booking.docstatus == 1:
		return {
			"success": True,
			"booking_name": booking.name,
			"booking_status": booking.booking_status,
			"payment_status": booking.payment_status,
			"message": "Booking is already confirmed and paid.",
		}

	if booking.booking_status == "Expired":
		frappe.throw(_("Cannot pay for an expired booking. Seats have already been released."))

	if booking.booking_status == "Cancelled":
		frappe.throw(_("Cannot pay for a cancelled booking."))

	if booking.booking_status != "Pending":
		frappe.throw(_("Cannot pay for a booking with status '{0}'.").format(booking.booking_status))

	# Submitting the document sets booking_status=Confirmed and payment_status=Paid
	booking.flags.ignore_permissions = True
	booking.submit()

	try:
		send_booking_confirmation(booking.name)
	except Exception:
		pass

	return {
		"success": True,
		"booking_name": booking.name,
		"booking_status": booking.booking_status,
		"payment_status": booking.payment_status,
		"message": f"Payment of ₹{booking.total_amount:,.2f} completed successfully! Your booking is now Confirmed.",
	}


@frappe.whitelist()
def cancel_booking(booking_name):
	"""
	Cancels a Ticket Booking and calculates refund per cancellation window policy.
	"""
	if not booking_name:
		frappe.throw(_("Booking name is required."))

	booking = frappe.get_doc("Ticket Booking", booking_name)
	user = frappe.session.user

	if user != "Administrator" and "System Manager" not in frappe.get_roles(user) and "Cinema Manager" not in frappe.get_roles(user):
		if booking.booked_by != user and booking.owner != user:
			frappe.throw(_("You are not authorized to cancel this booking."))

	if booking.booking_status == "Cancelled" or booking.docstatus == 2:
		return {"success": True, "message": "Booking is already cancelled."}

	if booking.docstatus == 1:
		booking.flags.ignore_permissions = True
		booking.cancel()
	else:
		booking.booking_status = "Cancelled"
		booking.payment_status = "Cancelled"
		booking.flags.ignore_permissions = True
		booking.save()

	return {
		"success": True,
		"booking_name": booking.name,
		"booking_status": "Cancelled",
		"payment_status": booking.payment_status,
		"refund_amount": booking.refund_amount or 0.0,
		"message": f"Booking {booking.name} cancelled. Refund amount: ₹{booking.refund_amount or 0.0:,.2f}",
	}


@frappe.whitelist()
def create_endgame_shows():
	"""Ensures Avengers: Endgame has active scheduled shows today and tomorrow."""
	shows_created = []

	# Show 1: Today 21:00 on PVR IMAX-Screen 1
	if not frappe.db.exists("Show", {"movie": "MOV-00003", "show_date": "2026-11-04"}):
		s1 = frappe.new_doc("Show")
		s1.movie = "MOV-00003"
		s1.screen = "PVR IMAX-Screen 1"
		s1.show_date = "2026-11-04"
		s1.start_time = "21:00:00"
		s1.ticket_price = 450.0
		s1.show_status = "Scheduled"
		s1.insert(ignore_permissions=True)
		shows_created.append(s1.name)

	# Show 2: Tomorrow 15:00 on PVR IMAX-Screen 3
	if not frappe.db.exists("Show", {"movie": "MOV-00003", "show_date": "2026-11-05"}):
		s2 = frappe.new_doc("Show")
		s2.movie = "MOV-00003"
		s2.screen = "PVR IMAX-Screen 3"
		s2.show_date = "2026-11-05"
		s2.start_time = "15:00:00"
		s2.ticket_price = 350.0
		s2.show_status = "Scheduled"
		s2.insert(ignore_permissions=True)
		shows_created.append(s2.name)

	frappe.db.commit()
	return {"success": True, "shows": shows_created}


@frappe.whitelist()
def bulk_create_shows(movie, screens, from_date, to_date, show_times, ticket_price=None, queue_now=False):
	"""
	Bulk creates Show records for a movie across multiple screens and date range at specified show times.
	Uses frappe.enqueue to process in background unless queue_now is True.
	"""
	if not movie:
		frappe.throw(_("Movie is required."))
	if not screens:
		frappe.throw(_("At least one screen is required."))
	if not from_date or not to_date:
		frappe.throw(_("From Date and To Date are required."))
	if not show_times:
		frappe.throw(_("At least one show time is required."))

	if isinstance(screens, str):
		try:
			screens = json.loads(screens)
		except Exception:
			screens = [s.strip() for s in screens.split(",") if s.strip()]

	if isinstance(show_times, str):
		try:
			show_times = json.loads(show_times)
		except Exception:
			show_times = [t.strip() for t in show_times.replace("\n", ",").split(",") if t.strip()]

	if not screens:
		frappe.throw(_("No valid screens provided."))
	if not show_times:
		frappe.throw(_("No valid show times provided."))

	f_date = getdate(from_date)
	t_date = getdate(to_date)
	if f_date > t_date:
		frappe.throw(_("From Date cannot be after To Date."))

	movie_doc = frappe.get_doc("Movie", movie)
	if movie_doc.movie_status == "Ended":
		frappe.throw(_("Cannot create shows for movie '{0}' because its status is 'Ended'.").format(movie_doc.title))

	user = frappe.session.user

	if frappe.utils.cint(queue_now):
		return _bulk_create_shows_job(
			movie=movie,
			screens=screens,
			from_date=str(f_date),
			to_date=str(t_date),
			show_times=show_times,
			ticket_price=ticket_price,
			user=user,
		)

	# Enqueue via frappe.enqueue (Section 4 Requirement 5)
	frappe.enqueue(
		"movie_tickets.api._bulk_create_shows_job",
		queue="default",
		timeout=600,
		movie=movie,
		screens=screens,
		from_date=str(f_date),
		to_date=str(t_date),
		show_times=show_times,
		ticket_price=ticket_price,
		user=user,
	)

	return {
		"success": True,
		"enqueued": True,
		"message": _("Bulk show creation queued in background for movie '{0}' across {1} screens.").format(
			movie_doc.title, len(screens)
		),
	}


def _bulk_create_shows_job(movie, screens, from_date, to_date, show_times, ticket_price=None, user=None):
	"""
	Worker job that runs in background (or synchronous if queued_now).
	Creates Show records for each date, screen, and show_time.
	"""
	f_date = getdate(from_date)
	t_date = getdate(to_date)
	days_count = (t_date - f_date).days + 1

	movie_doc = frappe.get_doc("Movie", movie)
	duration = movie_doc.duration_minutes or 120

	created_shows = []
	skipped_shows = []

	# Format times nicely: ensure HH:MM:00
	cleaned_times = []
	for st in show_times:
		st = str(st).strip()
		parts = st.split(":")
		if len(parts) == 1:
			st = f"{int(parts[0]):02d}:00:00"
		elif len(parts) == 2:
			st = f"{int(parts[0]):02d}:{int(parts[1]):02d}:00"
		elif len(parts) == 3:
			st = f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}"
		cleaned_times.append(st)

	price = flt(ticket_price) if ticket_price else None

	for i in range(days_count):
		cur_date = add_days(f_date, i)
		date_str = str(cur_date)

		for screen in screens:
			for time_str in cleaned_times:
				# Calculate tentative start and end time
				start_td = to_timedelta(time_str)
				end_td = start_td + timedelta(minutes=duration)

				# Check for conflicts on screen & date
				conflicting_shows = frappe.get_all(
					"Show",
					filters={
						"screen": screen,
						"show_date": date_str,
						"show_status": ["!=", "Cancelled"],
					},
					fields=["name", "start_time", "end_time"],
				)

				is_conflict = False
				for ex in conflicting_shows:
					ex_start = to_timedelta(ex.start_time)
					ex_end = to_timedelta(ex.end_time)
					if start_td < ex_end and end_td > ex_start:
						is_conflict = True
						skipped_shows.append({
							"screen": screen,
							"date": date_str,
							"time": time_str,
							"reason": f"Showtime conflict with {ex.name} ({ex.start_time} - {ex.end_time})",
						})
						break

				if is_conflict:
					continue

				# Create doc
				show_doc = frappe.new_doc("Show")
				show_doc.movie = movie
				show_doc.screen = screen
				show_doc.show_date = date_str
				show_doc.start_time = time_str
				if price:
					show_doc.ticket_price = price
				show_doc.show_status = "Scheduled"

				try:
					show_doc.insert(ignore_permissions=True)
					created_shows.append(show_doc.name)
				except Exception as e:
					skipped_shows.append({
						"screen": screen,
						"date": date_str,
						"time": time_str,
						"reason": str(e),
					})

	frappe.db.commit()

	msg = _("Bulk Show Creation complete: {0} shows created, {1} skipped.").format(
		len(created_shows), len(skipped_shows)
	)

	if user:
		try:
			frappe.publish_realtime(
				"msgprint",
				{"message": msg, "title": _("Bulk Show Creator"), "indicator": "green" if created_shows else "orange"},
				user=user,
			)
		except Exception:
			pass

	return {
		"success": True,
		"created_count": len(created_shows),
		"skipped_count": len(skipped_shows),
		"created_shows": created_shows,
		"skipped_shows": skipped_shows,
		"message": msg,
	}



