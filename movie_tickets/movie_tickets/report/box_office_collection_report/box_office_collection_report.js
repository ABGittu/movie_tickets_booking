// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.query_reports["Box Office Collection Report"] = {
	filters: [
		{
			fieldname: "theater",
			label: __("Theater"),
			fieldtype: "Link",
			options: "Theater",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "genre",
			label: __("Genre"),
			fieldtype: "Link",
			options: "Movie Genre",
		},
		{
			fieldname: "language",
			label: __("Language"),
			fieldtype: "Select",
			options: "\nEnglish\nHindi\nJapanese\nKorean\nSpanish\nFrench\nGerman\nItalian\nTamil\nTelugu\nMalayalam\nKannada\nBengali\nMarathi\nGujarati\nPunjabi",
		},
	],
	onload: function(report) {
		report.page.add_inner_button(__("Top 10 Movies (Bar)"), function() {
			if (frappe.query_report.raw_data && frappe.query_report.raw_data.chart_1) {
				frappe.query_report.render_chart(frappe.query_report.raw_data.chart_1);
			}
		}, __("Switch Chart"));

		report.page.add_inner_button(__("Screen Type Revenue (Pie)"), function() {
			if (frappe.query_report.raw_data && frappe.query_report.raw_data.chart_2) {
				frappe.query_report.render_chart(frappe.query_report.raw_data.chart_2);
			}
		}, __("Switch Chart"));
	}
};
