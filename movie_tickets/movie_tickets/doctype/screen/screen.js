// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Screen", {
	seat_rows(frm) {
		frm.trigger("calculate_total_seats");
	},
	seats_per_row(frm) {
		frm.trigger("calculate_total_seats");
	},
	calculate_total_seats(frm) {
		if (frm.doc.seat_rows && frm.doc.seats_per_row) {
			frm.set_value("total_seats", frm.doc.seat_rows * frm.doc.seats_per_row);
		}
	},
});
