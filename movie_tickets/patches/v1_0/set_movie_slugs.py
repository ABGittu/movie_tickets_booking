# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

import re

import frappe


def execute():
	"""Generate slug from title for all Movies where slug is NULL or empty."""
	frappe.reload_doc("movie_tickets", "doctype", "movie")

	if not frappe.db.has_column("Movie", "slug"):
		return

	movies = frappe.db.sql(
		"""
		SELECT name, title
		FROM `tabMovie`
		WHERE slug IS NULL OR slug = ''
		""",
		as_dict=True,
	)

	for m in movies:
		title = (m.title or "").strip()
		base_slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
		if not base_slug:
			base_slug = m.name.lower()

		# Ensure uniqueness
		slug = base_slug
		counter = 1
		while frappe.db.exists("Movie", {"slug": slug, "name": ["!=", m.name]}):
			slug = f"{base_slug}-{counter}"
			counter += 1

		frappe.db.set_value("Movie", m.name, "slug", slug, update_modified=False)

	frappe.db.commit()
