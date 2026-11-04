import frappe
from frappe.utils import today, format_date

def get_context(context):
	context.no_cache = 1

	movie_id = frappe.form_dict.get("movie")
	if not movie_id:
		# If title was passed or fallback
		movie_id = frappe.db.get_value("Movie", {"movie_status": "Now Showing"}, "name")
		if not movie_id:
			frappe.local.flags.redirect_location = "/now-showing"
			raise frappe.Redirect

	if not frappe.db.exists("Movie", movie_id):
		frappe.local.flags.redirect_location = "/now-showing"
		raise frappe.Redirect

	movie = frappe.get_doc("Movie", movie_id)
	context.movie = movie
	context.title = f"{movie.title} - Shows & Tickets"

	context.is_guest = (frappe.session.user == "Guest")
	context.user_email = "" if context.is_guest else frappe.session.user
	context.user_full_name = "" if context.is_guest else frappe.utils.get_fullname(frappe.session.user)
	context.user_phone = "" if context.is_guest else (frappe.db.get_value("User", frappe.session.user, "phone") or "")

	# Fetch upcoming shows
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
		as_dict=True
	)

	# Group shows by Theater and Date
	theaters_dict = {}
	for s in raw_shows:
		th_name = s.theater
		if th_name not in theaters_dict:
			theaters_dict[th_name] = {
				"theater_name": th_name,
				"city": s.city,
				"address": s.address,
				"dates": {}
			}

		d_str = str(s.show_date)
		if d_str not in theaters_dict[th_name]["dates"]:
			theaters_dict[th_name]["dates"][d_str] = {
				"date_str": d_str,
				"formatted_date": format_date(s.show_date, "medium"),
				"shows": []
			}

		theaters_dict[th_name]["dates"][d_str]["shows"].append(s)

	context.theaters_data = list(theaters_dict.values())
	context.total_shows_count = len(raw_shows)
