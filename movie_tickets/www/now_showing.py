import frappe
from frappe.utils import today


def get_context(context):
	context.no_cache = 1
	context.title = "Explore Movies & Shows"

	search_query = (frappe.form_dict.get("search") or "").strip()
	selected_status = frappe.form_dict.get("status") or "all"
	selected_genre = frappe.form_dict.get("genre") or ""
	selected_language = frappe.form_dict.get("language") or ""
	only_active_shows = frappe.form_dict.get("has_shows") == "1"

	# 1. Fetch upcoming active shows per movie
	shows_counts = frappe.db.sql(
		"""
		SELECT movie, COUNT(*) AS cnt
		FROM `tabShow`
		WHERE show_date >= %s
		  AND show_status IN ('Scheduled', 'Now Playing')
		GROUP BY movie
		""",
		(today(),),
		as_dict=True,
	)
	shows_map = {s.movie: s.cnt for s in shows_counts}

	# 2. Build SQL conditions for Movies
	conditions = ["1=1"]
	params = {}

	if selected_status and selected_status != "all":
		conditions.append("m.movie_status = %(status)s")
		params["status"] = selected_status

	if selected_genre:
		conditions.append("m.genre = %(genre)s")
		params["genre"] = selected_genre

	if selected_language:
		conditions.append("m.language = %(language)s")
		params["language"] = selected_language

	if search_query:
		conditions.append(
			"(m.title LIKE %(sq)s OR m.director LIKE %(sq)s OR m.cast_list LIKE %(sq)s OR m.synopsis LIKE %(sq)s)"
		)
		params["sq"] = f"%{search_query}%"

	where_clause = " AND ".join(conditions)

	movies = frappe.db.sql(
		f"""
		SELECT
			m.name,
			m.title,
			m.slug,
			m.language,
			m.genre,
			m.rating,
			m.duration_minutes,
			m.release_date,
			m.end_date,
			m.poster,
			m.synopsis,
			m.director,
			m.cast_list,
			m.movie_status
		FROM `tabMovie` m
		WHERE {where_clause}
		ORDER BY m.title ASC
		""",
		params,
		as_dict=True,
	)

	# 3. Enrich movies with show status & badge info
	enriched_movies = []
	for m in movies:
		active_count = shows_map.get(m.name, 0)
		m["active_shows_count"] = active_count
		m["has_active_shows"] = (active_count > 0)

		# If user toggled 'Only with active shows', filter out movies without shows
		if only_active_shows and active_count == 0:
			continue

		# Status Badge config
		st = m.movie_status or "Upcoming"
		if st == "Now Showing":
			if active_count > 0:
				m["badge_label"] = "Now Showing"
				m["badge_bg"] = "#276749"  # Deep green
				m["badge_color"] = "#ffffff"
			else:
				m["badge_label"] = "In Theaters (No Active Shows)"
				m["badge_bg"] = "#d69e2e"  # Amber/Orange
				m["badge_color"] = "#ffffff"
		elif st == "Upcoming":
			m["badge_label"] = "Upcoming"
			m["badge_bg"] = "#2b6cb0"  # Blue
			m["badge_color"] = "#ffffff"
		elif st == "Ended":
			m["badge_label"] = "Ended"
			m["badge_bg"] = "#718096"  # Slate/Gray
			m["badge_color"] = "#ffffff"
		else:
			m["badge_label"] = st
			m["badge_bg"] = "#4a5568"
			m["badge_color"] = "#ffffff"

		enriched_movies.append(m)

	# 4. Fetch dynamic languages (union of DB values + DocType options)
	db_langs = frappe.db.sql(
		"SELECT DISTINCT language FROM `tabMovie` WHERE language IS NOT NULL AND language != '' ORDER BY language",
		pluck="language",
	)
	doctype_lang_options = (
		frappe.get_meta("Movie").get_field("language").options or ""
	).split("\n")
	all_langs = sorted(list(set([l.strip() for l in (db_langs + doctype_lang_options) if l.strip()])))

	# 5. Fetch dynamic genres
	db_genres = frappe.db.sql(
		"SELECT DISTINCT name FROM `tabMovie Genre` WHERE is_active = 1 ORDER BY name",
		pluck="name",
	)
	if not db_genres:
		db_genres = frappe.db.sql(
			"SELECT DISTINCT genre FROM `tabMovie` WHERE genre IS NOT NULL AND genre != '' ORDER BY genre",
			pluck="genre",
		)
	all_genres = sorted(list(set([g.strip() for g in db_genres if g.strip()])))

	context.movies = enriched_movies
	context.total_count = len(enriched_movies)
	context.genres = all_genres
	context.languages = all_langs
	context.selected_genre = selected_genre
	context.selected_language = selected_language
	context.selected_status = selected_status
	context.search_query = search_query
	context.only_active_shows = only_active_shows
