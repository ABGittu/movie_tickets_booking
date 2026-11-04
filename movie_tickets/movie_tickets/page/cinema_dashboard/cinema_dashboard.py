# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today


@frappe.whitelist()
def get_dashboard_data():
	"""Bonus Task 4.3: Return analytics data for Cinema Dashboard charts and KPI summary."""
	today_date = today()

	# 1. KPI Summaries
	kpi_res = frappe.db.sql(
		"""
		SELECT
			COALESCE(SUM(total_amount), 0) AS total_revenue,
			COUNT(name) AS total_bookings,
			COALESCE(SUM(number_of_seats), 0) AS total_seats
		FROM `tabTicket Booking`
		WHERE booking_status = 'Confirmed'
		""",
		as_dict=True,
	)[0]

	today_res = frappe.db.sql(
		"""
		SELECT
			COALESCE(SUM(total_amount), 0) AS today_revenue,
			COUNT(name) AS today_bookings
		FROM `tabTicket Booking`
		WHERE booking_status = 'Confirmed'
		  AND DATE(creation) = %s
		""",
		(today_date,),
		as_dict=True,
	)[0]

	# 2. Chart 1: Today's Occupancy by Theater (Bar)
	theater_occupancy = frappe.db.sql(
		"""
		SELECT
			t.theater_name,
			COALESCE(SUM(s.total_seats), 0) AS capacity,
			COALESCE(SUM(s.booked_seats), 0) AS booked
		FROM `tabTheater` t
		LEFT JOIN `tabShow` s ON s.theater = t.name AND s.show_date = %s
		GROUP BY t.theater_name
		ORDER BY t.theater_name ASC
		""",
		(today_date,),
		as_dict=True,
	)
	chart1_labels = []
	chart1_values = []
	for to in theater_occupancy:
		chart1_labels.append(to.theater_name)
		occ_pct = round((float(to.booked) / float(to.capacity) * 100), 2) if to.capacity > 0 else 0.0
		chart1_values.append(occ_pct)

	chart_occupancy = {
		"data": {
			"labels": chart1_labels,
			"datasets": [
				{
					"name": _("Occupancy Rate (%)"),
					"values": chart1_values,
				}
			],
		},
		"type": "bar",
		"colors": ["#3b82f6"],
	}

	# 3. Chart 2: 30-day Revenue Trend (Line)
	trend_res = frappe.db.sql(
		"""
		SELECT DATE(creation) AS b_date, COALESCE(SUM(total_amount), 0) AS rev
		FROM `tabTicket Booking`
		WHERE booking_status = 'Confirmed'
		  AND creation >= DATE_SUB(%s, INTERVAL 30 DAY)
		GROUP BY DATE(creation)
		ORDER BY b_date ASC
		""",
		(today_date,),
		as_dict=True,
	)
	trend_map = {str(r.b_date): float(r.rev) for r in trend_res}

	chart2_labels = []
	chart2_values = []
	for i in range(29, -1, -1):
		d = str(add_days(today_date, -i))
		chart2_labels.append(d[-5:])  # MM-DD
		chart2_values.append(trend_map.get(d, 0.0))

	chart_revenue_trend = {
		"data": {
			"labels": chart2_labels,
			"datasets": [
				{
					"name": _("Revenue (₹)"),
					"values": chart2_values,
				}
			],
		},
		"type": "line",
		"colors": ["#10b981"],
	}

	# 4. Chart 3: Bookings by Time Slot (Histogram / Bar)
	slot_res = frappe.db.sql(
		"""
		SELECT
			CASE
				WHEN s.start_time < '12:00:00' THEN 'Morning (09-12)'
				WHEN s.start_time < '16:00:00' THEN 'Matinee (12-16)'
				WHEN s.start_time < '20:00:00' THEN 'Evening (16-20)'
				ELSE 'Night (20-24)'
			END AS slot,
			COUNT(tb.name) AS cnt,
			COALESCE(SUM(tb.number_of_seats), 0) AS seats
		FROM `tabTicket Booking` tb
		JOIN `tabShow` s ON s.name = tb.show
		WHERE tb.booking_status = 'Confirmed'
		GROUP BY slot
		ORDER BY slot ASC
		""",
		as_dict=True,
	)
	slot_order = [
		"Morning (09-12)",
		"Matinee (12-16)",
		"Evening (16-20)",
		"Night (20-24)",
	]
	slot_map = {r.slot: r.cnt for r in slot_res}
	chart3_labels = slot_order
	chart3_values = [slot_map.get(s, 0) for s in slot_order]

	chart_time_slots = {
		"data": {
			"labels": chart3_labels,
			"datasets": [
				{
					"name": _("Confirmed Bookings"),
					"values": chart3_values,
				}
			],
		},
		"type": "bar",
		"colors": ["#f59e0b"],
	}

	# 5. Chart 4: Top 5 Movies by Bookings (Donut)
	top_movies_res = frappe.db.sql(
		"""
		SELECT movie_title, COUNT(*) AS bookings_cnt
		FROM `tabTicket Booking`
		WHERE booking_status = 'Confirmed'
		GROUP BY movie_title
		ORDER BY bookings_cnt DESC, movie_title ASC
		LIMIT 5
		""",
		as_dict=True,
	)
	chart4_labels = [r.movie_title for r in top_movies_res] or ["No Data"]
	chart4_values = [int(r.bookings_cnt) for r in top_movies_res] or [0]

	chart_top_movies = {
		"data": {
			"labels": chart4_labels,
			"datasets": [
				{
					"name": _("Bookings"),
					"values": chart4_values,
				}
			],
		},
		"type": "donut",
		"colors": ["#6366f1", "#ec4899", "#8b5cf6", "#3b82f6", "#14b8a6"],
	}

	return {
		"kpis": {
			"total_revenue": float(kpi_res.total_revenue or 0.0),
			"total_bookings": int(kpi_res.total_bookings or 0),
			"total_seats": int(kpi_res.total_seats or 0),
			"today_revenue": float(today_res.today_revenue or 0.0),
			"today_bookings": int(today_res.today_bookings or 0),
		},
		"chart_occupancy": chart_occupancy,
		"chart_revenue_trend": chart_revenue_trend,
		"chart_time_slots": chart_time_slots,
		"chart_top_movies": chart_top_movies,
	}
