# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MovieGenre(Document):
	def validate(self):
		self.validate_duplicate_genre()

	def validate_duplicate_genre(self):
		"""Validate no duplicate genre_name (case-insensitive check)."""
		if not self.genre_name:
			return

		existing = frappe.db.sql(
			"""
			SELECT name FROM `tabMovie Genre`
			WHERE LOWER(genre_name) = LOWER(%s) AND name != %s
			""",
			(self.genre_name.strip(), self.name or ""),
			as_dict=True,
		)
		if existing:
			frappe.throw(_("Movie Genre '{0}' already exists.").format(self.genre_name))
