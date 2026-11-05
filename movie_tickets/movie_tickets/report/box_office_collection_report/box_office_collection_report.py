# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("from_date"):
		filters.from_date = frappe.utils.add_months(frappe.utils.today(), -1)
	if not filters.get("to_date"):
		filters.to_date = frappe.utils.add_months(frappe.utils.today(), 1)

	columns = get_columns()
	data = get_data(filters)
	chart_1, chart_2 = get_charts(data, filters)
	report_summary = get_report_summary(data)

	if filters.get("chart_type") == "Screen Type Revenue (Pie)":
		selected_chart = chart_2
	else:
		selected_chart = chart_1

	# Attach both charts so client-side buttons can easily switch
	selected_chart["chart_1"] = chart_1
	selected_chart["chart_2"] = chart_2
	chart_1["chart_1"] = chart_1
	chart_1["chart_2"] = chart_2
	chart_2["chart_1"] = chart_1
	chart_2["chart_2"] = chart_2

	message = {"chart_1": chart_1, "chart_2": chart_2}

	return columns, data, message, selected_chart, report_summary


def get_columns():
	return [
		{
			"label": _("Movie Title"),
			"fieldname": "movie_title",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Genre"),
			"fieldname": "genre",
			"fieldtype": "Link",
			"options": "Movie Genre",
			"width": 120,
		},
		{
			"label": _("Language"),
			"fieldname": "language",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Total Shows"),
			"fieldname": "total_shows",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Total Bookings"),
			"fieldname": "total_bookings",
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"label": _("Total Seats Sold"),
			"fieldname": "total_seats_sold",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Total Revenue"),
			"fieldname": "total_revenue",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Avg Occupancy (%)"),
			"fieldname": "avg_occupancy",
			"fieldtype": "Percent",
			"width": 130,
		},
		{
			"label": _("Avg Ticket Price"),
			"fieldname": "avg_ticket_price",
			"fieldtype": "Currency",
			"width": 120,
		},
	]


def get_data(filters):
	movie_conditions = []
	show_conditions = []
	params = {}

	if filters.get("genre"):
		movie_conditions.append("m.genre = %(genre)s")
		params["genre"] = filters.genre

	if filters.get("language"):
		movie_conditions.append("m.language = %(language)s")
		params["language"] = filters.language

	if filters.get("theater"):
		show_conditions.append("s.theater = %(theater)s")
		params["theater"] = filters.theater

	if filters.get("from_date"):
		show_conditions.append("s.show_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		show_conditions.append("s.show_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	m_where = f"WHERE {' AND '.join(movie_conditions)}" if movie_conditions else ""
	s_extra = f"AND {' AND '.join(show_conditions)}" if show_conditions else ""

	# Query movies matching genre/language
	movies = frappe.db.sql(
		f"""
		SELECT m.name AS movie, m.title AS movie_title, m.genre, m.language
		FROM `tabMovie` m
		{m_where}
		ORDER BY m.title ASC
		""",
		params,
		as_dict=True,
	)

	data = []
	for m in movies:
		p = params.copy()
		p["movie"] = m.movie

		# 1. Shows stats for this movie
		shows_stat = frappe.db.sql(
			f"""
			SELECT
				COUNT(s.name) AS total_shows,
				COALESCE(SUM(s.total_seats), 0) AS total_capacity
			FROM `tabShow` s
			WHERE s.movie = %(movie)s
			{s_extra}
			""",
			p,
			as_dict=True,
		)[0]

		# 2. Confirmed Bookings stats for this movie
		b_extra = ""
		if filters.get("theater"):
			b_extra += " AND s.theater = %(theater)s"
		if filters.get("from_date"):
			b_extra += " AND s.show_date >= %(from_date)s"
		if filters.get("to_date"):
			b_extra += " AND s.show_date <= %(to_date)s"

		bookings_stat = frappe.db.sql(
			f"""
			SELECT
				COUNT(tb.name) AS total_bookings,
				COALESCE(SUM(tb.number_of_seats), 0) AS total_seats_sold,
				COALESCE(SUM(tb.total_amount), 0) AS total_revenue
			FROM `tabTicket Booking` tb
			JOIN `tabShow` s ON s.name = tb.show
			WHERE s.movie = %(movie)s
			  AND tb.booking_status = 'Confirmed'
			{b_extra}
			""",
			p,
			as_dict=True,
		)[0]

		total_shows = shows_stat.total_shows or 0
		total_capacity = shows_stat.total_capacity or 0
		total_bookings = bookings_stat.total_bookings or 0
		total_seats_sold = bookings_stat.total_seats_sold or 0
		total_revenue = float(bookings_stat.total_revenue or 0.0)

		# If user filtered by theater or date, and there are no shows and no bookings, skip
		if (
			(filters.get("theater") or filters.get("from_date") or filters.get("to_date"))
			and total_shows == 0
			and total_bookings == 0
		):
			continue

		avg_occupancy = round((total_seats_sold / total_capacity * 100), 2) if total_capacity > 0 else 0.0
		avg_ticket_price = round(total_revenue / total_seats_sold, 2) if total_seats_sold > 0 else 0.0

		data.append({
			"movie_title": m.movie_title,
			"genre": m.genre,
			"language": m.language,
			"total_shows": total_shows,
			"total_bookings": total_bookings,
			"total_seats_sold": total_seats_sold,
			"total_revenue": total_revenue,
			"avg_occupancy": avg_occupancy,
			"avg_ticket_price": avg_ticket_price,
		})

	# Sort by revenue descending
	data.sort(key=lambda d: d["total_revenue"], reverse=True)
	return data


def get_charts(data, filters):
	# Chart 1: Bar chart — top 10 movies by revenue
	sorted_by_revenue = sorted(data, key=lambda d: d["total_revenue"], reverse=True)[:10]
	top_10 = [d for d in sorted_by_revenue if d["total_revenue"] > 0]
	if not top_10 and sorted_by_revenue:
		top_10 = sorted_by_revenue[:5]

	chart_1 = {
		"data": {
			"labels": [d["movie_title"] for d in top_10],
			"datasets": [
				{
					"name": _("Revenue (₹)"),
					"values": [d["total_revenue"] for d in top_10],
				}
			],
		},
		"type": "bar",
		"colors": ["#3b82f6"],
	}

	# Chart 2: Pie chart — revenue by screen type (Standard / IMAX / 3D / 4DX)
	screen_where = []
	p = {}
	if filters.get("theater"):
		screen_where.append("s.theater = %(theater)s")
		p["theater"] = filters.theater
	if filters.get("from_date"):
		screen_where.append("s.show_date >= %(from_date)s")
		p["from_date"] = filters.from_date
	if filters.get("to_date"):
		screen_where.append("s.show_date <= %(to_date)s")
		p["to_date"] = filters.to_date
	if filters.get("genre"):
		screen_where.append("m.genre = %(genre)s")
		p["genre"] = filters.genre
	if filters.get("language"):
		screen_where.append("m.language = %(language)s")
		p["language"] = filters.language

	extra_join = (
		"JOIN `tabMovie` m ON m.name = s.movie"
		if (filters.get("genre") or filters.get("language"))
		else ""
	)
	where_clause = f"AND {' AND '.join(screen_where)}" if screen_where else ""

	screen_res = frappe.db.sql(
		f"""
		SELECT
			sc.screen_type,
			COALESCE(SUM(tb.total_amount), 0) AS revenue
		FROM `tabTicket Booking` tb
		JOIN `tabShow` s ON s.name = tb.show
		JOIN `tabScreen` sc ON sc.name = s.screen
		{extra_join}
		WHERE tb.booking_status = 'Confirmed'
		{where_clause}
		GROUP BY sc.screen_type
		ORDER BY revenue DESC
		""",
		p,
		as_dict=True,
	)

	screen_labels = [r.screen_type for r in screen_res if float(r.revenue or 0) > 0]
	screen_values = [float(r.revenue) for r in screen_res if float(r.revenue or 0) > 0]

	if not screen_labels:
		screen_labels = [r.screen_type for r in screen_res] or ["Standard", "IMAX", "3D", "4DX"]
		screen_values = [float(r.revenue) for r in screen_res] or [0, 0, 0, 0]

	chart_2 = {
		"data": {
			"labels": screen_labels,
			"datasets": [
				{
					"name": _("Revenue by Screen Type"),
					"values": screen_values,
				}
			],
		},
		"type": "pie",
		"colors": ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b"],
	}

	return chart_1, chart_2


def get_report_summary(data):
	total_revenue = sum(d["total_revenue"] for d in data)
	total_seats = sum(d["total_seats_sold"] for d in data)
	total_bookings = sum(d["total_bookings"] for d in data)
	avg_ticket_price = round(total_revenue / total_seats, 2) if total_seats > 0 else 0.0

	return [
		{
			"value": total_revenue,
			"indicator": "Green",
			"label": _("Total Box Office Revenue"),
			"datatype": "Currency",
		},
		{
			"value": total_seats,
			"indicator": "Blue",
			"label": _("Total Seats Sold"),
			"datatype": "Int",
		},
		{
			"value": total_bookings,
			"indicator": "Purple",
			"label": _("Total Bookings"),
			"datatype": "Int",
		},
		{
			"value": avg_ticket_price,
			"indicator": "Orange",
			"label": _("Avg Ticket Price"),
			"datatype": "Currency",
		},
	]
