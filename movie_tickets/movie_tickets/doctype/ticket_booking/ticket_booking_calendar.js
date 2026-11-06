// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.views.calendar["Ticket Booking"] = {
	field_map: {
		start: "show_date",
		end: "show_date",
		id: "name",
		title: "movie_title",
		status: "booking_status",
		allDay: "all_day",
	},
	style_map: {
		Confirmed: "success",
		Pending: "warning",
		Cancelled: "danger",
	},
	filters: [
		{
			fieldtype: "Link",
			fieldname: "theater",
			options: "Theater",
			label: __("Theater"),
		},
		{
			fieldtype: "Select",
			fieldname: "booking_status",
			options: "\nPending\nConfirmed\nCancelled",
			label: __("Booking Status"),
		},
	],
	get_events_method: "frappe.desk.calendar.get_events",
};
