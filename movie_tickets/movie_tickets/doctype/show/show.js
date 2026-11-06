// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Show", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("View Bookings"), () => {
				frappe.set_route("List", "Ticket Booking", { show: frm.doc.name });
			});

			// Dashboard indicators
			const total = frm.doc.total_seats || 0;
			const booked = frm.doc.booked_seats || 0;
			const available = frm.doc.available_seats || 0;
			const occupancy = total > 0 ? ((booked / total) * 100).toFixed(1) : 0;

			let occupancyColor = "green";
			if (occupancy >= 100) occupancyColor = "red";
			else if (occupancy > 80) occupancyColor = "orange";

			frm.dashboard.clear_headline();
			frm.dashboard.set_headline(
				`Booked: <span class="indicator-pill blue">${booked}</span> | ` +
					`Available: <span class="indicator-pill green">${available}</span> | ` +
					`Occupancy: <span class="indicator-pill ${occupancyColor}">${occupancy}%</span>`
			);
		}
	},

	screen(frm) {
		if (frm.doc.screen) {
			frappe.db.get_value(
				"Screen",
				frm.doc.screen,
				["base_price", "total_seats", "theater"],
				(r) => {
					if (r) {
						if (!frm.doc.ticket_price) {
							frm.set_value("ticket_price", r.base_price);
						}
						frm.set_value("total_seats", r.total_seats);
						frm.set_value("theater", r.theater);
						if (frm.is_new()) {
							frm.set_value("available_seats", r.total_seats);
							frm.set_value("booked_seats", 0);
						}
					}
				}
			);
		}
	},

	movie(frm) {
		frm.trigger("calculate_end_time");
	},

	start_time(frm) {
		frm.trigger("calculate_end_time");
	},

	calculate_end_time(frm) {
		if (frm.doc.movie && frm.doc.start_time) {
			frappe.db.get_value("Movie", frm.doc.movie, "duration_minutes", (r) => {
				if (r && r.duration_minutes) {
					const duration = parseInt(r.duration_minutes, 10);
					const parts = frm.doc.start_time.split(":");
					const hours = parseInt(parts[0], 10);
					const minutes = parseInt(parts[1], 10);

					const totalMinutes = hours * 60 + minutes + duration;
					const endHours = Math.floor(totalMinutes / 60) % 24;
					const endMins = totalMinutes % 60;

					const pad = (n) => String(n).padStart(2, "0");
					const calculated = `${pad(endHours)}:${pad(endMins)}:00`;
					frm.set_value("end_time", calculated);

					frappe.msgprint({
						message: __("Movie duration is {0} mins. Calculated end time: {1}", [
							duration,
							calculated,
						]),
						indicator: "blue",
					});
				}
			});
		}
	},
});
