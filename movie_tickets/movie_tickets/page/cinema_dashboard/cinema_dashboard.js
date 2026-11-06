// Copyright (c) 2026, Abhijit P Dodiya and contributors
// For license information, please see license.txt

frappe.pages["cinema-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Cinema Analytics Dashboard"),
		single_column: true,
	});

	page.add_inner_button(__("Refresh"), () => {
		load_dashboard(page);
	});

	page.main.html(`
		<div class="cinema-dashboard-container" style="padding: 15px;">
			<!-- KPI Row -->
			<div class="row mb-4" id="kpi-cards-row">
				<div class="col-md-3 mb-3">
					<div class="card p-3 shadow-sm border" style="border-radius: 10px;">
						<div class="text-muted small text-uppercase font-weight-bold">Total Box Office Revenue</div>
						<div class="h3 font-weight-bold text-success mb-0" id="kpi-total-revenue">₹0.00</div>
					</div>
				</div>
				<div class="col-md-3 mb-3">
					<div class="card p-3 shadow-sm border" style="border-radius: 10px;">
						<div class="text-muted small text-uppercase font-weight-bold">Today's Revenue</div>
						<div class="h3 font-weight-bold text-primary mb-0" id="kpi-today-revenue">₹0.00</div>
					</div>
				</div>
				<div class="col-md-3 mb-3">
					<div class="card p-3 shadow-sm border" style="border-radius: 10px;">
						<div class="text-muted small text-uppercase font-weight-bold">Confirmed Bookings</div>
						<div class="h3 font-weight-bold text-info mb-0" id="kpi-total-bookings">0</div>
					</div>
				</div>
				<div class="col-md-3 mb-3">
					<div class="card p-3 shadow-sm border" style="border-radius: 10px;">
						<div class="text-muted small text-uppercase font-weight-bold">Total Seats Sold</div>
						<div class="h3 font-weight-bold text-warning mb-0" id="kpi-total-seats">0</div>
					</div>
				</div>
			</div>

			<!-- Charts Grid -->
			<div class="row">
				<!-- Chart 1: Occupancy by Theater -->
				<div class="col-lg-6 mb-4">
					<div class="card p-3 shadow-sm border" style="border-radius: 10px; height: 100%;">
						<h6 class="font-weight-bold mb-3">📊 Today's Occupancy by Theater</h6>
						<div id="chart-theater-occupancy" style="height: 300px;"></div>
					</div>
				</div>

				<!-- Chart 2: 30-Day Revenue Trend -->
				<div class="col-lg-6 mb-4">
					<div class="card p-3 shadow-sm border" style="border-radius: 10px; height: 100%;">
						<h6 class="font-weight-bold mb-3">📈 30-Day Revenue Trend (Line)</h6>
						<div id="chart-revenue-trend" style="height: 300px;"></div>
					</div>
				</div>

				<!-- Chart 3: Bookings by Time Slot -->
				<div class="col-lg-6 mb-4">
					<div class="card p-3 shadow-sm border" style="border-radius: 10px; height: 100%;">
						<h6 class="font-weight-bold mb-3">⏰ Bookings by Time Slot (Histogram)</h6>
						<div id="chart-time-slots" style="height: 300px;"></div>
					</div>
				</div>

				<!-- Chart 4: Top 5 Movies by Bookings -->
				<div class="col-lg-6 mb-4">
					<div class="card p-3 shadow-sm border" style="border-radius: 10px; height: 100%;">
						<h6 class="font-weight-bold mb-3">🍩 Top 5 Movies by Bookings (Donut)</h6>
						<div id="chart-top-movies" style="height: 300px;"></div>
					</div>
				</div>
			</div>
		</div>
	`);

	load_dashboard(page);
};

function load_dashboard(page) {
	frappe.call({
		method: "movie_tickets.movie_tickets.page.cinema_dashboard.cinema_dashboard.get_dashboard_data",
		freeze: true,
		freeze_message: __("Loading Analytics Dashboard..."),
		callback: function (r) {
			if (!r.message) return;
			const data = r.message;

			// Populate KPIs
			if (data.kpis) {
				$("#kpi-total-revenue").text(
					"₹" +
						data.kpis.total_revenue.toLocaleString("en-IN", {
							minimumFractionDigits: 2,
						})
				);
				$("#kpi-today-revenue").text(
					"₹" +
						data.kpis.today_revenue.toLocaleString("en-IN", {
							minimumFractionDigits: 2,
						})
				);
				$("#kpi-total-bookings").text(data.kpis.total_bookings);
				$("#kpi-total-seats").text(data.kpis.total_seats);
			}

			// Render Chart 1: Occupancy
			if (data.chart_occupancy) {
				new frappe.Chart("#chart-theater-occupancy", {
					title: "",
					data: data.chart_occupancy.data,
					type: "bar",
					height: 280,
					colors: ["#3b82f6"],
				});
			}

			// Render Chart 2: Revenue Trend
			if (data.chart_revenue_trend) {
				new frappe.Chart("#chart-revenue-trend", {
					title: "",
					data: data.chart_revenue_trend.data,
					type: "line",
					height: 280,
					colors: ["#10b981"],
					lineOptions: {
						regionFill: 1,
					},
				});
			}

			// Render Chart 3: Time slots
			if (data.chart_time_slots) {
				new frappe.Chart("#chart-time-slots", {
					title: "",
					data: data.chart_time_slots.data,
					type: "bar",
					height: 280,
					colors: ["#f59e0b"],
				});
			}

			// Render Chart 4: Top movies
			if (data.chart_top_movies) {
				new frappe.Chart("#chart-top-movies", {
					title: "",
					data: data.chart_top_movies.data,
					type: "donut",
					height: 280,
					colors: ["#6366f1", "#ec4899", "#8b5cf6", "#3b82f6", "#14b8a6"],
				});
			}
		},
	});
}
