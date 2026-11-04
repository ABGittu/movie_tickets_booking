// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.listview_settings["Movie"] = {
	add_fields: ["title", "language", "genre", "rating", "release_date", "movie_status"],
	get_indicator(doc) {
		if (doc.movie_status === "Now Showing") {
			return [__("Now Showing"), "green", "movie_status,=,Now Showing"];
		} else if (doc.movie_status === "Upcoming") {
			return [__("Upcoming"), "blue", "movie_status,=,Upcoming"];
		} else if (doc.movie_status === "Ended") {
			return [__("Ended"), "gray", "movie_status,=,Ended"];
		}
	}
};
