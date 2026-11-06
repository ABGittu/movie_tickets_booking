// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.ui.form.on("Movie", {
	title(frm) {
		if (frm.doc.title && !frm.doc.slug) {
			const slug = frm.doc.title
				.toLowerCase()
				.trim()
				.replace(/[^a-z0-9]+/g, "-")
				.replace(/^-+|-+$/g, "");
			frm.set_value("slug", slug);
		}
	},
});
