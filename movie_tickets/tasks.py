# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

import datetime
import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, getdate, now_datetime, today


def auto_expire_unpaid_bookings():
	"""Find Ticket Bookings where booking_status = 'Pending', payment_status = 'Unpaid',
	and booking_time older than booking_expiry_minutes.
	Set booking_status to 'Expired'.
	Release seats on the Show by recalculating from confirmed bookings.
	"""
	expiry_mins = frappe.db.get_single_value("Booking Configuration", "booking_expiry_minutes") or 15
	cutoff = add_to_date(now_datetime(), minutes=-int(expiry_mins))

	pending_bookings = frappe.get_all(
		"Ticket Booking",
		filters={
			"booking_status": "Pending",
			"payment_status": "Unpaid",
			"docstatus": 0,
		},
		fields=["name", "show", "number_of_seats", "booking_time", "creation"],
	)

	expired_count = 0
	shows_to_update = set()
	for b in pending_bookings:
		b_time = b.booking_time or b.creation
		if b_time and get_datetime(b_time) <= cutoff:
			doc = frappe.get_doc("Ticket Booking", b.name)
			doc.db_set("booking_status", "Expired")
			if doc.show:
				shows_to_update.add(doc.show)

			expired_count += 1
			frappe.logger("movie_tickets").info(
				f"Auto-expired unpaid booking {doc.name} and released seats on Show {doc.show}"
			)

	for show_name in shows_to_update:
		if frappe.db.exists("Show", show_name):
			recalculate_show_seats(show_name)

	return expired_count


def recalculate_show_seats(show_name):
	"""Recalculate booked_seats and available_seats for a Show based on actual Confirmed bookings."""
	if not show_name or not frappe.db.exists("Show", show_name):
		return

	total_seats = frappe.db.get_value("Show", show_name, "total_seats") or 0
	count_res = frappe.db.sql(
		"""
		SELECT COUNT(bs.name) AS booked_count
		FROM `tabBooked Seat` bs
		JOIN `tabTicket Booking` tb ON tb.name = bs.parent
		WHERE tb.show = %s
		  AND tb.booking_status = 'Confirmed'
		  AND tb.docstatus = 1
		""",
		(show_name,),
		as_dict=True,
	)
	booked_count = count_res[0].booked_count if count_res else 0
	available = max(0, total_seats - booked_count)

	frappe.db.set_value(
		"Show",
		show_name,
		{
			"booked_seats": booked_count,
			"available_seats": available,
		},
		update_modified=False,
	)


def update_movie_status():
	"""Daily: Recalculate movie_status for all movies based on today vs release_date and end_date."""
	today_date = getdate(today())
	movies = frappe.get_all("Movie", fields=["name", "release_date", "end_date", "movie_status"])
	updated_count = 0

	for m in movies:
		if not m.release_date:
			continue

		rel_date = getdate(m.release_date)
		e_date = getdate(m.end_date) if m.end_date else None

		if today_date < rel_date:
			new_status = "Upcoming"
		elif e_date and today_date > e_date:
			new_status = "Ended"
		else:
			new_status = "Now Showing"

		if new_status != m.movie_status:
			frappe.db.set_value("Movie", m.name, "movie_status", new_status)
			updated_count += 1

	return updated_count


def update_show_status():
	"""Hourly:
	- Shows where show_date < today -> Completed.
	- Shows where show_date = today and start_time passed but end_time not -> Now Playing.
	- Shows where show_date = today and end_time passed -> Completed.
	"""
	today_date = getdate(today())
	now_dt = now_datetime()
	current_time = now_dt.time()

	# 1. Past dates: all scheduled/playing shows are marked Completed
	frappe.db.sql(
		"""
		UPDATE `tabShow`
		SET show_status = 'Completed'
		WHERE show_date < %s
		  AND show_status IN ('Scheduled', 'Now Playing')
		""",
		(today_date,),
	)

	# 2. Today's shows
	today_shows = frappe.get_all(
		"Show",
		filters={"show_date": today_date, "show_status": ["in", ["Scheduled", "Now Playing"]]},
		fields=["name", "start_time", "end_time", "show_status"],
	)

	updated_count = 0
	for s in today_shows:
		start_t = s.start_time
		if isinstance(start_t, datetime.timedelta):
			start_t = (datetime.datetime.min + start_t).time()
		elif isinstance(start_t, str):
			start_t = datetime.time.fromisoformat(start_t)

		end_t = s.end_time
		if isinstance(end_t, datetime.timedelta):
			end_t = (datetime.datetime.min + end_t).time()
		elif isinstance(end_t, str):
			end_t = datetime.time.fromisoformat(end_t)

		if end_t and current_time >= end_t:
			new_status = "Completed"
		elif start_t and current_time >= start_t:
			new_status = "Now Playing"
		else:
			new_status = "Scheduled"

		if new_status != s.show_status:
			frappe.db.set_value("Show", s.name, "show_status", new_status)
			updated_count += 1

	return updated_count


def daily_revenue_digest():
	"""Daily at 11 PM:
	Calculate today's total bookings, revenue, and top movie.
	Send HTML email to Cinema Managers.
	"""
	today_date = today()

	# 1. Today's bookings count & revenue
	data = frappe.db.sql(
		"""
		SELECT
			COUNT(*) AS total_bookings,
			COALESCE(SUM(total_amount), 0) AS total_revenue,
			COALESCE(SUM(number_of_seats), 0) AS total_seats
		FROM `tabTicket Booking`
		WHERE DATE(creation) = %s
		  AND booking_status = 'Confirmed'
		""",
		(today_date,),
		as_dict=True,
	)[0]

	# 2. Top movie today by revenue
	top_movie_res = frappe.db.sql(
		"""
		SELECT movie_title, SUM(total_amount) AS rev, COUNT(*) AS b_cnt
		FROM `tabTicket Booking`
		WHERE DATE(creation) = %s
		  AND booking_status = 'Confirmed'
		GROUP BY movie_title
		ORDER BY rev DESC
		LIMIT 1
		""",
		(today_date,),
		as_dict=True,
	)
	top_movie_name = top_movie_res[0].movie_title if top_movie_res else "None"
	top_movie_rev = top_movie_res[0].rev if top_movie_res else 0.0

	# 3. Find Cinema Managers
	cinema_managers = frappe.get_all(
		"Has Role",
		filters={"role": "Cinema Manager", "parenttype": "User"},
		fields=["parent"],
		distinct=True,
	)
	recipients = [m.parent for m in cinema_managers if m.parent and m.parent not in ("Administrator", "Guest")]
	if not recipients:
		recipients = ["administrator@example.com"]

	subject = f"Daily Cinema Revenue Digest - {today_date}"
	message = f"""
	<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
		<h2 style="color: #2b6cb0; margin-top: 0;">🎬 Daily Cinema Revenue Digest</h2>
		<p style="color: #4a5568;">Summary of cinema operations and ticket bookings for <strong>{today_date}</strong>:</p>
		
		<table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
			<tr style="background: #f7fafc; border-bottom: 1px solid #edf2f7;">
				<td style="padding: 10px 14px; font-weight: 600;">Total Confirmed Bookings:</td>
				<td style="padding: 10px 14px; font-weight: bold; text-align: right;">{data.total_bookings}</td>
			</tr>
			<tr style="border-bottom: 1px solid #edf2f7;">
				<td style="padding: 10px 14px; font-weight: 600;">Total Seats Sold:</td>
				<td style="padding: 10px 14px; font-weight: bold; text-align: right;">{data.total_seats}</td>
			</tr>
			<tr style="background: #f7fafc; border-bottom: 1px solid #edf2f7;">
				<td style="padding: 10px 14px; font-weight: 600;">Total Revenue:</td>
				<td style="padding: 10px 14px; font-weight: bold; color: #276749; text-align: right;">₹{float(data.total_revenue):,.2f}</td>
			</tr>
			<tr>
				<td style="padding: 10px 14px; font-weight: 600;">Top Performing Movie:</td>
				<td style="padding: 10px 14px; font-weight: bold; color: #2b6cb0; text-align: right;">{top_movie_name} (₹{float(top_movie_rev):,.2f})</td>
			</tr>
		</table>

		<p style="font-size: 13px; color: #718096; margin-top: 25px;">
			Generated automatically by Movie Tickets App.
		</p>
	</div>
	"""

	try:
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=message,
			delayed=True,
		)
	except Exception as e:
		frappe.logger("movie_tickets").warning(f"Could not send daily revenue email: {e}")

	return {
		"total_bookings": data.total_bookings,
		"total_revenue": data.total_revenue,
		"top_movie": top_movie_name,
	}
