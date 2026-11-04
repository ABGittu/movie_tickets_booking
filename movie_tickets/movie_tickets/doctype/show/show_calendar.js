// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.views.calendar["Show"] = {
	field_map: {
		start: "show_date",
		end: "show_date",
		id: "name",
		title: "movie_title",
		status: "show_status",
		allDay: "all_day"
	},
	style_map: {
		"Scheduled": "success",
		"Now Playing": "warning",
		"Completed": "secondary",
		"Cancelled": "danger"
	},
	filters: [
		{
			fieldtype: "Link",
			fieldname: "theater",
			options: "Theater",
			label: __("Theater")
		},
		{
			fieldtype: "Link",
			fieldname: "screen",
			options: "Screen",
			label: __("Screen")
		},
		{
			fieldtype: "Select",
			fieldname: "show_status",
			options: "\nScheduled\nNow Playing\nCompleted\nCancelled",
			label: __("Status")
		}
	],
	get_events_method: "frappe.desk.calendar.get_events"
};
