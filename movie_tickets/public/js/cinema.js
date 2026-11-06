// ==========================================================================
// Movie Tickets Desk Javascript (Task 3.2 C)
// ==========================================================================

console.log("Movie Tickets App Loaded");

frappe.provide("movie_tickets");

$(document).ready(function () {
	// Register Ctrl+Shift+B shortcut to open new Ticket Booking form
	frappe.ui.keys.add_shortcut({
		shortcut: "ctrl+shift+b",
		action: function () {
			if (frappe.new_doc) {
				frappe.new_doc("Ticket Booking");
			} else {
				frappe.set_route("Form", "Ticket Booking", "new-ticket-booking-1");
			}
		},
		description: __("Open New Ticket Booking"),
		ignore_inputs: true,
		page: null,
	});
});
