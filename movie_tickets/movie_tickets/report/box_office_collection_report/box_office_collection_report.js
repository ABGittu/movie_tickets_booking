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
			default: frappe.datetime.add_months(frappe.datetime.get_today(), 1),
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
		{
			fieldname: "chart_type",
			label: __("Chart Type"),
			fieldtype: "Select",
			options: "Top 10 Movies (Bar)\nScreen Type Revenue (Pie)",
			default: "Top 10 Movies (Bar)",
		},
	],
	onload: function(report) {
		report.page.add_inner_button(__("Top 10 Movies (Bar)"), function() {
			let chart = frappe.query_report.chart_1 || frappe.query_report.raw_data?.chart?.chart_1 || frappe.query_report.raw_data?.message?.chart_1 || frappe.query_report.raw_data?.chart;
			if (chart) {
				frappe.query_report.render_chart(chart);
			}
		}, __("Switch Chart"));

		report.page.add_inner_button(__("Screen Type Revenue (Pie)"), function() {
			let chart = frappe.query_report.chart_2 || frappe.query_report.raw_data?.chart?.chart_2 || frappe.query_report.raw_data?.message?.chart_2;
			if (chart) {
				frappe.query_report.render_chart(chart);
			}
		}, __("Switch Chart"));
	},
	after_datatable_render: function(report) {
		let chart_data = frappe.query_report.raw_data?.chart || frappe.query_report.raw_data?.message;
		if (chart_data) {
			if (chart_data.chart_1) frappe.query_report.chart_1 = chart_data.chart_1;
			if (chart_data.chart_2) frappe.query_report.chart_2 = chart_data.chart_2;
		}
	}
};
