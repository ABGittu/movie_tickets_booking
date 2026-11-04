import frappe


def execute():
	"""
	Section 4 Patch: Generate and attach QR codes for any Confirmed Ticket Bookings
	that do not have a qr_code populated.
	"""
	bookings = frappe.get_all(
		"Ticket Booking",
		filters={"booking_status": "Confirmed", "qr_code": ["in", ["", None]]},
		pluck="name",
	)
	for bkg_name in bookings:
		doc = frappe.get_doc("Ticket Booking", bkg_name)
		try:
			doc.generate_and_attach_qr_code()
		except Exception:
			pass
