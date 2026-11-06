// Cinema Portal Global Theme Switcher
(function () {
	const STORAGE_KEY = "cinema_theme";

	function getSavedTheme() {
		try {
			return localStorage.getItem(STORAGE_KEY) || "light";
		} catch (e) {
			return "light";
		}
	}

	function applyTheme(theme) {
		const isDark = theme === "dark";

		// 1. Root data-theme attribute (essential for Frappe and standard web frameworks)
		document.documentElement.setAttribute("data-theme", theme);
		document.documentElement.setAttribute("data-theme-mode", theme);
		if (document.body) {
			document.body.setAttribute("data-theme", theme);
			document.body.classList.remove("dark-portal-theme");
		}
		try {
			localStorage.removeItem("cinema_portal_theme");
		} catch (e) {
			// ignore storage errors
		}

		// 2. Class toggling on both html and body for bulletproof selector matching
		if (isDark) {
			document.documentElement.classList.add("dark", "dark-theme");
			document.documentElement.classList.remove("light", "light-theme");
			if (document.body) {
				document.body.classList.add("dark", "dark-theme");
				document.body.classList.remove("light", "light-theme");
			}
		} else {
			document.documentElement.classList.remove("dark", "dark-theme");
			document.documentElement.classList.add("light", "light-theme");
			if (document.body) {
				document.body.classList.remove("dark", "dark-theme");
				document.body.classList.add("light", "light-theme");
			}
		}

		try {
			localStorage.setItem(STORAGE_KEY, theme);
		} catch (e) {
			// ignore storage errors
		}

		updateButtons(isDark);
	}

	function updateButtons(isDark) {
		// When Dark mode is currently active, clicking button will switch to Light Mode
		// When Light mode is currently active, clicking button will switch to Dark Mode
		const label = isDark ? "Light Mode" : "Dark Mode";
		const icon = isDark ? "☀️" : "🌙";

		document.querySelectorAll(".cinema-theme-toggle, #theme-toggle-btn").forEach((btn) => {
			const iconEl = btn.querySelector("#theme-icon, .toggle-icon");
			const textEl = btn.querySelector("#theme-text, .toggle-text");
			if (iconEl) iconEl.textContent = icon;
			if (textEl) textEl.textContent = label;
			if (!iconEl && !textEl) {
				btn.innerHTML = `${icon} <span>${label}</span>`;
			}
			btn.setAttribute("title", `Switch to ${label}`);
		});
	}

	// Apply immediately while <head> is parsing to prevent flash of wrong mode
	applyTheme(getSavedTheme());

	function setupThemeUI() {
		applyTheme(getSavedTheme());

		// Global delegated click handler
		document.removeEventListener("click", handleToggleClick);
		document.addEventListener("click", handleToggleClick);

		// Inject into navbar if not already there
		injectNavbarItem();
	}

	function handleToggleClick(e) {
		const btn = e.target.closest(".cinema-theme-toggle, #theme-toggle-btn");
		if (btn) {
			e.preventDefault();
			const current = getSavedTheme();
			const nextTheme = current === "dark" ? "light" : "dark";
			applyTheme(nextTheme);
		}
	}

	function injectNavbarItem() {
		if (document.querySelector(".cinema-navbar-theme-item")) return;

		// Prefer .navbar-nav.ml-auto (right side of navbar), fallback to any navbar-nav
		const navbarList = document.querySelector(
			".navbar .navbar-nav.ml-auto, .navbar .navbar-nav"
		);
		if (navbarList) {
			const li = document.createElement("li");
			li.className = "nav-item cinema-navbar-theme-item d-flex align-items-center ml-2 mr-2";
			const isDark = getSavedTheme() === "dark";
			li.innerHTML = `
				<button type="button" class="cinema-theme-toggle shadow-sm" title="Switch to ${
					isDark ? "Light Mode" : "Dark Mode"
				}" style="margin-left: 8px;">
					<span class="toggle-icon">${isDark ? "☀️" : "🌙"}</span>
					<span class="toggle-text">${isDark ? "Light Mode" : "Dark Mode"}</span>
				</button>
			`;
			navbarList.appendChild(li);
		}
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", setupThemeUI);
	} else {
		setupThemeUI();
	}

	if (window.frappe && frappe.ready) {
		frappe.ready(setupThemeUI);
	}
})();
