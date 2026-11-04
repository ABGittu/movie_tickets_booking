// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.listview_settings["Show"] = {
	add_fields: ["movie_title", "screen", "show_date", "start_time", "available_seats", "show_status"],
	get_indicator(doc) {
		if (doc.show_status === "Scheduled") {
			return [__("Scheduled"), "green", "show_status,=,Scheduled"];
		} else if (doc.show_status === "Now Playing") {
			return [__("Now Playing"), "orange", "show_status,=,Now Playing"];
		} else if (doc.show_status === "Completed") {
			return [__("Completed"), "gray", "show_status,=,Completed"];
		} else if (doc.show_status === "Cancelled") {
			return [__("Cancelled"), "red", "show_status,=,Cancelled"];
		}
	}
};
