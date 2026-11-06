# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class Movie(Document):
	def validate(self):
		self.validate_duration()
		self.validate_dates()

	def before_save(self):
		self.generate_slug()
		self.set_movie_status()

	def validate_duration(self):
		"""Validate duration_minutes is between 1 and 600."""
		if not self.duration_minutes or self.duration_minutes < 1 or self.duration_minutes > 600:
			frappe.throw(_("Duration must be between 1 and 600 minutes."))

	def validate_dates(self):
		"""Validate that end_date > release_date if end_date is set."""
		if self.end_date and self.release_date:
			if getdate(self.end_date) <= getdate(self.release_date):
				frappe.throw(_("End Date must be greater than Release Date."))

	def generate_slug(self):
		"""Auto-generate slug from title on before_save."""
		if self.title and (not self.slug or self.is_new() or self.has_value_changed("title")):
			base_slug = re.sub(r"[^a-zA-Z0-9]+", "-", self.title.strip().lower()).strip("-")
			slug = base_slug
			counter = 1
			# Ensure uniqueness
			while frappe.db.exists("Movie", {"slug": slug, "name": ["!=", self.name or ""]}):
				slug = f"{base_slug}-{counter}"
				counter += 1
			self.slug = slug

	def set_movie_status(self):
		"""Auto-compute movie_status based on release_date and end_date vs today."""
		if not self.release_date:
			return

		today_date = getdate(today())
		rel_date = getdate(self.release_date)
		e_date = getdate(self.end_date) if self.end_date else None

		if today_date < rel_date:
			self.movie_status = "Upcoming"
		elif e_date and today_date > e_date:
			self.movie_status = "Ended"
		else:
			self.movie_status = "Now Showing"
