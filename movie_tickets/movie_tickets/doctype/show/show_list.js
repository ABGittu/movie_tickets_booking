// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.listview_settings["Show"] = {
	add_fields: [
		"movie_title",
		"screen",
		"show_date",
		"start_time",
		"available_seats",
		"show_status",
	],
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
	},
	onload(listview) {
		listview.page.add_inner_button(__("Bulk Create Shows 🎬"), () => {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Screen",
					fields: ["name", "screen_name", "theater"],
					limit_page_length: 100,
					order_by: "theater asc, screen_name asc",
				},
				callback: (r) => {
					const screens = r.message || [];
					if (!screens.length) {
						frappe.msgprint(__("No screens found. Please create screens first."));
						return;
					}

					const screen_options = screens.map((s) => ({
						label: `${s.screen_name} (${s.theater})`,
						value: s.name,
						checked: 0,
					}));

					const dialog = new frappe.ui.Dialog({
						title: __("Bulk Show Creator 🎬"),
						fields: [
							{
								fieldname: "movie",
								label: __("Select Movie"),
								fieldtype: "Link",
								options: "Movie",
								reqd: 1,
								get_query: () => ({
									filters: { movie_status: ["!=", "Ended"] },
								}),
							},
							{
								fieldname: "col_break_1",
								fieldtype: "Column Break",
							},
							{
								fieldname: "ticket_price",
								label: __("Override Ticket Price (₹)"),
								fieldtype: "Currency",
								description: __("Optional. Leave empty to use screen base price."),
							},
							{
								fieldname: "sec_dates",
								label: __("Schedule Window"),
								fieldtype: "Section Break",
							},
							{
								fieldname: "from_date",
								label: __("From Date"),
								fieldtype: "Date",
								reqd: 1,
								default: frappe.datetime.get_today(),
							},
							{
								fieldname: "to_date",
								label: __("To Date"),
								fieldtype: "Date",
								reqd: 1,
								default: frappe.datetime.add_days(frappe.datetime.get_today(), 2),
							},
							{
								fieldname: "show_times",
								label: __("Show Times (Comma Separated)"),
								fieldtype: "Small Text",
								reqd: 1,
								default: "10:00, 14:00, 18:00, 21:30",
								description: __(
									"Enter daily start times, e.g. 10:00, 14:00, 18:00, 21:30"
								),
							},
							{
								fieldname: "sec_screens",
								label: __("Select Screens"),
								fieldtype: "Section Break",
							},
							{
								fieldname: "screens",
								label: __("Screens"),
								fieldtype: "MultiCheck",
								options: screen_options,
								columns: 2,
								reqd: 1,
							},
						],
						primary_action_label: __("Schedule Shows in Bulk"),
						primary_action(values) {
							const selected_screens = dialog.fields_dict.screens.get_value();
							if (!selected_screens || !selected_screens.length) {
								frappe.msgprint(__("Please select at least one screen."));
								return;
							}

							dialog
								.get_primary_btn()
								.prop("disabled", true)
								.text(__("Creating..."));

							frappe.call({
								method: "movie_tickets.api.bulk_create_shows",
								args: {
									movie: values.movie,
									screens: selected_screens,
									from_date: values.from_date,
									to_date: values.to_date,
									show_times: values.show_times,
									ticket_price: values.ticket_price || null,
								},
								freeze: true,
								freeze_message: __("Scheduling shows in background..."),
								callback: (res) => {
									dialog.hide();
									if (res.message && res.message.success) {
										frappe.show_alert(
											{
												message: res.message.message,
												indicator: "green",
											},
											7
										);
										setTimeout(() => listview.refresh(), 1000);
									}
								},
								always: () => {
									dialog
										.get_primary_btn()
										.prop("disabled", false)
										.text(__("Schedule Shows in Bulk"));
								},
							});
						},
					});

					dialog.show();
				},
			});
		});
	},
};
