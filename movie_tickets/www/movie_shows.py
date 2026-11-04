import frappe
from datetime import datetime, time, timedelta
from frappe.utils import add_days, format_date, getdate, now_datetime, today


def get_context(context):
	context.no_cache = 1

	movie_id = frappe.form_dict.get("movie")
	if not movie_id:
		# Fallback to The Dark Knight or first Now Showing movie
		movie_id = frappe.db.get_value("Movie", {"title": "The Dark Knight"}, "name") or frappe.db.get_value("Movie", {"movie_status": "Now Showing"}, "name")
		if not movie_id:
			frappe.local.flags.redirect_location = "/now-showing"
			raise frappe.Redirect

	if not frappe.db.exists("Movie", movie_id):
		# Try title search if ID doesn't match directly
		by_title = frappe.db.get_value("Movie", {"title": movie_id}, "name")
		if by_title:
			movie_id = by_title
		else:
			frappe.local.flags.redirect_location = "/now-showing"
			raise frappe.Redirect

	movie = frappe.get_doc("Movie", movie_id)
	context.movie = movie
	context.title = f"{movie.title} - Shows & Tickets"

	# User & session info
	is_guest = (frappe.session.user == "Guest")
	context.is_guest = is_guest
	context.user_email = "" if is_guest else frappe.session.user
	context.user_full_name = "" if is_guest else frappe.utils.get_fullname(frappe.session.user)
	context.user_phone = "" if is_guest else (frappe.db.get_value("User", frappe.session.user, "phone") or "")

	# Booking configuration
	open_days = frappe.db.get_single_value("Booking Configuration", "booking_open_days_before") or 7
	max_seats_per_booking = frappe.db.get_single_value("Booking Configuration", "max_seats_per_booking") or 10
	context.max_seats = max_seats_per_booking

	now = now_datetime()
	curr_date = getdate(today())
	curr_time = now.time()
	max_allowed_date = add_days(curr_date, open_days)

	# Fetch shows for the movie (Scheduled and Now Playing, on or after today)
	raw_shows = frappe.db.sql(
		"""
		SELECT
			s.name AS show_name,
			s.movie,
			s.movie_title,
			s.theater,
			s.screen,
			sc.screen_type,
			s.show_date,
			s.start_time,
			s.end_time,
			s.ticket_price,
			s.available_seats,
			s.total_seats,
			s.show_status,
			t.city,
			t.address
		FROM `tabShow` s
		JOIN `tabScreen` sc ON sc.name = s.screen
		JOIN `tabTheater` t ON t.name = s.theater
		WHERE s.movie = %s
		  AND s.show_status IN ('Scheduled', 'Now Playing')
		  AND s.show_date >= %s
		ORDER BY s.theater ASC, s.show_date ASC, s.start_time ASC
		""",
		(movie_id, today()),
		as_dict=True,
	)

	# Group shows by Theater and Date and compute booking eligibility
	theaters_dict = {}
	bookable_shows_count = 0

	for s in raw_shows:
		# Format start_time cleanly (handles timedelta or string/time)
		st = s.start_time
		if isinstance(st, timedelta):
			tot_secs = int(st.total_seconds())
			hours = tot_secs // 3600
			mins = (tot_secs % 3600) // 60
			st_time = time(hours, mins)
		elif isinstance(st, time):
			st_time = st
		else:
			parts = [int(p) for p in str(st).split(":")[:2]]
			st_time = time(parts[0], parts[1])

		s["time_display"] = st_time.strftime("%I:%M %p")
		s["time_24"] = st_time.strftime("%H:%M")

		# Format end_time if present
		et = s.end_time
		if et:
			if isinstance(et, timedelta):
				tot_secs = int(et.total_seconds())
				et_time = time((tot_secs // 3600) % 24, (tot_secs % 3600) // 60)
			elif isinstance(et, time):
				et_time = et
			else:
				parts = [int(p) for p in str(et).split(":")[:2]]
				et_time = time(parts[0] % 24, parts[1])
			s["end_time_display"] = et_time.strftime("%I:%M %p")
		else:
			s["end_time_display"] = ""

		# Determine booking eligibility:
		# 1. Show status must be Scheduled or Now Playing
		# 2. Must not be in the past (date > today OR (date == today AND time > now))
		# 3. Must be within booking window (show_date <= today + open_days)
		# 4. Available seats must be > 0
		is_bookable = True
		btn_label = "Book Now"
		reason = ""

		if s.show_status not in ["Scheduled", "Now Playing"]:
			is_bookable = False
			btn_label = s.show_status
			reason = f"Show is {s.show_status}"
		elif s.show_date < curr_date or (s.show_date == curr_date and st_time <= curr_time):
			is_bookable = False
			btn_label = "Show Started"
			reason = "This show has already commenced."
		elif s.show_date > getdate(max_allowed_date):
			is_bookable = False
			btn_label = "Opens Soon"
			reason = f"Booking opens {open_days} days before the show."
		elif (s.available_seats or 0) <= 0:
			is_bookable = False
			btn_label = "Housefull"
			reason = "All seats for this show are fully booked."

		s["is_bookable"] = is_bookable
		s["btn_label"] = btn_label
		s["reason"] = reason

		if is_bookable:
			bookable_shows_count += 1

		# Theater Grouping
		th_name = s.theater
		if th_name not in theaters_dict:
			theaters_dict[th_name] = {
				"theater_name": th_name,
				"city": s.city,
				"address": s.address,
				"dates": {},
			}

		d_str = str(s.show_date)
		if d_str not in theaters_dict[th_name]["dates"]:
			theaters_dict[th_name]["dates"][d_str] = {
				"date_str": d_str,
				"formatted_date": format_date(s.show_date, "medium"),
				"shows": [],
			}

		theaters_dict[th_name]["dates"][d_str]["shows"].append(s)

	context.theaters_data = list(theaters_dict.values())
	context.total_shows_count = len(raw_shows)
	context.bookable_shows_count = bookable_shows_count
