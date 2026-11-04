# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Screen(Document):
	def autoname(self):
		if self.theater and self.screen_name:
			self.name = f"{self.theater}-{self.screen_name}"

	def validate(self):
		self.validate_seats()

	def on_update(self):
		self.update_theater_screens()
		# If theater was changed, update previous theater too
		prev = self.get_doc_before_save()
		if prev and prev.theater and prev.theater != self.theater:
			self.update_theater_screens_for(prev.theater)

	def on_trash(self):
		self.update_theater_screens(exclude_self=True)

	def validate_seats(self):
		"""Validate that total_seats = seat_rows * seats_per_row."""
		expected = (self.seat_rows or 0) * (self.seats_per_row or 0)
		if self.total_seats != expected:
			frappe.throw(
				_("Total seats ({0}) must equal seat rows ({1}) * seats per row ({2}) = {3}.").format(
					self.total_seats, self.seat_rows, self.seats_per_row, expected
				)
			)

	def update_theater_screens(self, exclude_self=False):
		"""On save or delete, auto-update Theater's total_screens count."""
		if not self.theater:
			return
		self.update_theater_screens_for(self.theater, exclude_self=exclude_self)

	def update_theater_screens_for(self, theater_name, exclude_self=False):
		filters = {"theater": theater_name}
		if exclude_self:
			filters["name"] = ["!=", self.name]
		count = frappe.db.count("Screen", filters)
		frappe.db.set_value("Theater", theater_name, "total_screens", count)
