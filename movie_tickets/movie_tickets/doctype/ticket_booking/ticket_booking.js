// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Ticket Booking", {
	refresh(frm) {
		if (frm.doc.show) {
			frm.trigger("render_show_intro");
		}
	},

	show(frm) {
		if (frm.doc.show) {
			frappe.db.get_value("Show", frm.doc.show, [
				"movie_title", "theater", "screen", "show_date", "start_time", "ticket_price", "available_seats"
			], (r) => {
				if (r) {
					frm.set_value("movie_title", r.movie_title);
					frm.set_value("theater", r.theater);
					frm.set_value("screen", r.screen);
					frm.set_value("show_date", r.show_date);
					frm.set_value("start_time", r.start_time);
					frm.set_value("price_per_seat", r.ticket_price);

					frm.trigger("render_show_intro");

					if (r.available_seats !== undefined && r.available_seats < 5) {
						frappe.show_alert({
							message: __("Only {0} seats remaining!", [r.available_seats]),
							indicator: "orange"
						});
					}
				}
			});
		}
	},

	render_show_intro(frm) {
		if (!frm.doc.show) return;
		frappe.db.get_value("Show", frm.doc.show, ["available_seats", "ticket_price"], (r) => {
			const avail = r ? r.available_seats : "";
			const price = frm.doc.price_per_seat || (r ? r.ticket_price : "");
			const introText = `<b>Movie:</b> ${frm.doc.movie_title || ""} | <b>Theater:</b> ${frm.doc.theater || ""} | <b>Screen:</b> ${frm.doc.screen || ""} | <b>Date:</b> ${frm.doc.show_date || ""} ${frm.doc.start_time || ""} | <b>Price:</b> ₹${price} | <b>Available Seats:</b> ${avail}`;
			frm.set_intro(introText, "blue");
		});
	},

	seats_add(frm) {
		frm.trigger("calculate_totals");
	},

	seats_remove(frm) {
		frm.trigger("calculate_totals");
	},

	calculate_totals(frm) {
		const seats = frm.doc.seats || [];
		const seat_count = seats.length;
		frm.set_value("number_of_seats", seat_count);
		const price = frm.doc.price_per_seat || 0;
		frm.set_value("total_amount", seat_count * price);
	}
});

frappe.ui.form.on("Booked Seat", {
	seats_add(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.seat_price && frm.doc.price_per_seat) {
			frappe.model.set_value(cdt, cdn, "seat_price", frm.doc.price_per_seat);
		}
		frm.trigger("calculate_totals");
	},
	seats_remove(frm) {
		frm.trigger("calculate_totals");
	},
	seat_price(frm) {
		frm.trigger("calculate_totals");
	}
});
