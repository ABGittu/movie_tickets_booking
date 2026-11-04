import frappe
from frappe.utils import format_date

def get_context(context):
	context.no_cache = 1

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/my-bookings"
		raise frappe.Redirect

	user = frappe.session.user
	context.title = "My Bookings"
	context.user = user

	# Administrator can see all bookings, regular users only see their own
	if user == "Administrator" or "System Manager" in frappe.get_roles(user) or "Cinema Manager" in frappe.get_roles(user):
		bookings = frappe.get_all(
			"Ticket Booking",
			fields=[
				"name", "movie_title", "theater", "screen", "show_date",
				"start_time", "number_of_seats", "total_amount", "booking_status",
				"payment_status", "booking_time", "customer_name"
			],
			order_by="creation desc"
		)
	else:
		bookings = frappe.get_all(
			"Ticket Booking",
			filters={"booked_by": user},
			fields=[
				"name", "movie_title", "theater", "screen", "show_date",
				"start_time", "number_of_seats", "total_amount", "booking_status",
				"payment_status", "booking_time", "customer_name"
			],
			order_by="creation desc"
		)

	# Fetch child seats for each booking
	for b in bookings:
		seats = frappe.get_all(
			"Booked Seat",
			filters={"parent": b.name},
			pluck="seat_label",
			order_by="idx asc"
		)
		b["seats_list"] = ", ".join(seats) if seats else f"{b.number_of_seats} seats"
		b["formatted_date"] = format_date(b.show_date, "medium") if b.show_date else ""

		status = b.booking_status or "Pending"
		if status == "Confirmed":
			b["status_class"] = "badge-success"
			b["badge_bg"] = "#c6f6d5"
			b["badge_color"] = "#22543d"
		elif status == "Pending":
			b["status_class"] = "badge-warning"
			b["badge_bg"] = "#feebc8"
			b["badge_color"] = "#7b341e"
		elif status == "Cancelled":
			b["status_class"] = "badge-danger"
			b["badge_bg"] = "#fed7d7"
			b["badge_color"] = "#742a2a"
		else:
			b["status_class"] = "badge-secondary"
			b["badge_bg"] = "#e2e8f0"
			b["badge_color"] = "#4a5568"

	context.bookings = bookings
	context.total_count = len(bookings)
