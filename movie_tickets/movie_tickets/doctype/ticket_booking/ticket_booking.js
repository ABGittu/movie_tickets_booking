// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Ticket Booking", {
	refresh(frm) {
		if (frm.doc.show) {
			frm.trigger("render_show_intro");
		}

		// Custom button: Select Seats (in draft)
		if (frm.doc.docstatus === 0 && frm.doc.show) {
			frm.add_custom_button(__("Select Seats"), () => {
				frm.trigger("open_seat_selector");
			}).addClass("btn-primary");
		}

		// Custom button: Send Booking Confirmation (after submit)
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Send Booking Confirmation"), () => {
				frappe.call({
					method: "movie_tickets.api.send_booking_confirmation",
					args: { booking_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Sending confirmation email..."),
					callback: function (r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: __(r.message.message),
								indicator: "green"
							});
						}
					}
				});
			});
		}
	},

	before_cancel(frm) {
		return new Promise((resolve, reject) => {
			frappe.confirm(
				__(
					"Are you sure you want to cancel this booking?<br><br>" +
					"<b>Cancellation & Refund Policy:</b><br>" +
					"• More than 4 hours before show: <b>100% refund</b><br>" +
					"• 2 to 4 hours before show: <b>50% refund</b><br>" +
					"• Less than 2 hours before show: <b>No refund (0%)</b>"
				),
				() => resolve(),
				() => reject()
			);
		});
	},

	show(frm) {
		if (frm.doc.show) {
			frappe.db.get_value(
				"Show",
				frm.doc.show,
				["movie_title", "theater", "screen", "show_date", "start_time", "ticket_price", "available_seats"],
				(r) => {
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
						frm.refresh();
					}
				}
			);
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
	},

	open_seat_selector(frm) {
		frappe.call({
			method: "movie_tickets.api.get_seat_availability",
			args: { show_name: frm.doc.show },
			freeze: true,
			freeze_message: __("Loading seat layout..."),
			callback: function (r) {
				if (!r.message) return;
				const data = r.message;
				const currentSeats = new Set((frm.doc.seats || []).map((s) => s.seat_label));
				const selected = new Set(currentSeats);

				let gridHtml = `
					<div class="seat-map-wrapper" style="user-select: none;">
						<div style="text-align:center; background:#2d3748; color:#cbd5e0; font-size:12px; font-weight:bold; letter-spacing:2px; padding:6px; margin:0 auto 15px auto; width:80%; border-radius:4px; box-shadow:0 2px 4px rgba(0,0,0,0.2);">
							SCREEN THIS WAY
						</div>
						<div style="display:flex; justify-content:center; gap:20px; margin-bottom:15px; font-size:13px;">
							<span><span style="display:inline-block; width:16px; height:16px; background:#16a34a; border-radius:3px; vertical-align:middle; margin-right:5px;"></span> Available (Green)</span>
							<span><span style="display:inline-block; width:16px; height:16px; background:#eab308; border-radius:3px; vertical-align:middle; margin-right:5px;"></span> Selected (Yellow)</span>
							<span><span style="display:inline-block; width:16px; height:16px; background:#dc2626; border-radius:3px; vertical-align:middle; margin-right:5px;"></span> Booked (Red)</span>
						</div>
						<div style="overflow-x:auto; padding:10px 0; max-height:420px;">
							<table style="margin:0 auto; border-collapse:separate; border-spacing:6px;">
				`;

				data.seat_grid.forEach((row) => {
					gridHtml += `<tr>`;
					row.forEach((seat) => {
						const isBooked = seat.status === "booked";
						const isSelected = selected.has(seat.seat_label);

						let bg = "#16a34a";
						let fg = "#ffffff";
						let cursor = "pointer";
						let cls = "seat-btn available-seat";

						if (isBooked) {
							bg = "#dc2626";
							fg = "#ffffff";
							cursor = "not-allowed";
							cls = "seat-btn booked-seat";
						} else if (isSelected) {
							bg = "#eab308";
							fg = "#000000";
							cls = "seat-btn selected-seat";
						}

						gridHtml += `
							<td>
								<button type="button" class="${cls}" data-seat="${seat.seat_label}" data-booked="${isBooked ? 1 : 0}"
									style="width:36px; height:32px; background:${bg}; color:${fg}; font-size:11px; font-weight:bold; border:none; border-radius:4px; cursor:${cursor}; transition:all 0.15s ease;">
									${seat.seat_label}
								</button>
							</td>
						`;
					});
					gridHtml += `</tr>`;
				});

				gridHtml += `
							</table>
						</div>
						<div style="text-align:center; margin-top:10px; font-size:13px;">
							Selected Seats: <strong id="selected-seats-display">${Array.from(selected).join(", ") || "None"}</strong> |
							Count: <strong id="selected-count-display">${selected.size}</strong>
						</div>
					</div>
				`;

				const dialog = new frappe.ui.Dialog({
					title: __("Select Seats - {0}", [data.screen]),
					size: "large",
					fields: [
						{
							fieldtype: "HTML",
							fieldname: "seat_grid_html",
							options: gridHtml
						}
					],
					primary_action_label: __("Confirm Selection"),
					primary_action: function () {
						if (selected.size === 0) {
							frappe.msgprint(__("Please select at least one seat."));
							return;
						}
						if (selected.size > 10) {
							frappe.msgprint(__("You can select a maximum of 10 seats per booking."));
							return;
						}

						frm.clear_table("seats");
						const price = frm.doc.price_per_seat || data.ticket_price || 0;
						Array.from(selected).sort().forEach((s_label) => {
							const parts = s_label.split("-");
							const row = frm.add_child("seats");
							row.seat_label = s_label;
							row.row_letter = parts[0];
							row.seat_number = parseInt(parts[1], 10) || 1;
							row.seat_price = price;
						});

						frm.refresh_field("seats");
						frm.trigger("calculate_totals");
						dialog.hide();
					}
				});

				dialog.show();

				dialog.$wrapper.find(".seat-btn").on("click", function () {
					const btn = $(this);
					if (btn.data("booked") == 1) return;

					const seatLabel = btn.data("seat");
					if (selected.has(seatLabel)) {
						selected.delete(seatLabel);
						btn.css({ background: "#16a34a", color: "#ffffff" }).removeClass("selected-seat").addClass("available-seat");
					} else {
						if (selected.size >= 10) {
							frappe.show_alert({
								message: __("Maximum 10 seats allowed per booking."),
								indicator: "red"
							});
							return;
						}
						selected.add(seatLabel);
						btn.css({ background: "#eab308", color: "#000000" }).removeClass("available-seat").addClass("selected-seat");
					}

					dialog.$wrapper.find("#selected-seats-display").text(Array.from(selected).join(", ") || "None");
					dialog.$wrapper.find("#selected-count-display").text(selected.size);
				});
			}
		});
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
