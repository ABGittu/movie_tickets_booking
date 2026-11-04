// Cinema Portal Global Theme Switcher
(function() {
	const STORAGE_KEY = "cinema_theme";

	function getSavedTheme() {
		return localStorage.getItem(STORAGE_KEY) || "light";
	}

	function applyTheme(theme) {
		const isDark = (theme === "dark");
		
		// Remove any legacy classes
		if (document.body) {
			document.body.classList.remove("dark-portal-theme");
		}
		localStorage.removeItem("cinema_portal_theme");

		if (isDark) {
			document.documentElement.classList.add("dark-theme");
			if (document.body) document.body.classList.add("dark-theme");
		} else {
			document.documentElement.classList.remove("dark-theme");
			if (document.body) document.body.classList.remove("dark-theme");
		}

		localStorage.setItem(STORAGE_KEY, theme);
		updateButtons(isDark);
	}

	function updateButtons(isDark) {
		const label = isDark ? "Light Mode" : "Dark Mode";
		const icon = isDark ? "☀️" : "🌙";

		document.querySelectorAll(".cinema-theme-toggle, #theme-toggle-btn").forEach(btn => {
			const iconEl = btn.querySelector("#theme-icon, .toggle-icon");
			const textEl = btn.querySelector("#theme-text, .toggle-text");
			if (iconEl) iconEl.textContent = icon;
			if (textEl) textEl.textContent = label;
			if (!iconEl && !textEl) {
				btn.innerHTML = `${icon} <span>${label}</span>`;
			}
		});
	}

	// Apply immediately to avoid white flash
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
			const nextTheme = (current === "dark") ? "light" : "dark";
			applyTheme(nextTheme);
		}
	}

	function injectNavbarItem() {
		if (document.querySelector(".cinema-navbar-theme-item")) return;

		const navbarList = document.querySelector(".navbar .navbar-nav, header .navbar-nav");
		if (navbarList) {
			const li = document.createElement("li");
			li.className = "nav-item cinema-navbar-theme-item d-flex align-items-center ml-2 mr-2";
			const isDark = (getSavedTheme() === "dark");
			li.innerHTML = `
				<button type="button" class="cinema-theme-toggle shadow-sm" title="Toggle Light / Dark Mode" style="margin-left: 10px;">
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
