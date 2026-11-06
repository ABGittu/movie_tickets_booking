# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class Theater(Document):
	def validate(self):
		self.append_city_to_name()

	def autoname(self):
		self.append_city_to_name()
		self.name = self.theater_name

	def append_city_to_name(self):
		"""Append city name to theater name if not already present (e.g. 'PVR - Ahmedabad')."""
		if self.theater_name and self.city:
			suffix = f" - {self.city}"
			if not self.theater_name.endswith(suffix):
				self.theater_name = f"{self.theater_name}{suffix}"
