// Cinema Portal Global Theme Switcher
(function() {
	function getPreferredTheme() {
		return localStorage.getItem("cinema_theme") || "dark";
	}

	function applyGlobalTheme(theme) {
		const isDark = (theme === "dark");
		if (isDark) {
			document.documentElement.classList.add("dark-theme");
			if (document.body) document.body.classList.add("dark-theme");
		} else {
			document.documentElement.classList.remove("dark-theme");
			if (document.body) document.body.classList.remove("dark-theme");
		}
		localStorage.setItem("cinema_theme", theme);

		// Update all toggle buttons on page
		updateToggleButtons(isDark);
	}

	function updateToggleButtons(isDark) {
		const label = isDark ? "Light Mode" : "Dark Mode";
		const icon = isDark ? "☀️" : "🌙";

		document.querySelectorAll(".cinema-theme-toggle, #theme-toggle-btn").forEach(btn => {
			const iconSpan = btn.querySelector("#theme-icon, .toggle-icon");
			const textSpan = btn.querySelector("#theme-text, .toggle-text");
			if (iconSpan) iconSpan.textContent = icon;
			if (textSpan) textSpan.textContent = label;
			if (!iconSpan && !textSpan) {
				btn.innerHTML = `${icon} <span>${label}</span>`;
			}
		});
	}

	// Apply immediately to prevent white flash
	applyGlobalTheme(getPreferredTheme());

	// Setup on DOM Ready
	function initThemeUI() {
		const isDark = (getPreferredTheme() === "dark");
		applyGlobalTheme(isDark ? "dark" : "light");

		// Attach to all toggle buttons
		document.addEventListener("click", function(e) {
			const target = e.target.closest(".cinema-theme-toggle, #theme-toggle-btn");
			if (target) {
				e.preventDefault();
				const currentlyDark = document.documentElement.classList.contains("dark-theme");
				applyGlobalTheme(currentlyDark ? "light" : "dark");
			}
		});

		// Inject toggle into navbar if not present
		injectNavbarToggle();
	}

	function injectNavbarToggle() {
		if (document.querySelector(".navbar-theme-item")) return;

		const nav = document.querySelector(".navbar .navbar-nav, header .navbar-nav");
		if (nav) {
			const li = document.createElement("li");
			li.className = "nav-item navbar-theme-item d-flex align-items-center ml-2 mr-2";
			const isDark = (getPreferredTheme() === "dark");
			li.innerHTML = `
				<button type="button" class="cinema-theme-toggle" title="Toggle Theme" style="margin-left: 8px;">
					<span class="toggle-icon">${isDark ? "☀️" : "🌙"}</span>
					<span class="toggle-text">${isDark ? "Light Mode" : "Dark Mode"}</span>
				</button>
			`;
			nav.appendChild(li);
		}
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", initThemeUI);
	} else {
		initThemeUI();
	}

	if (window.frappe && frappe.ready) {
		frappe.ready(initThemeUI);
	}
})();
