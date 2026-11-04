import frappe
from frappe.utils import today

def get_context(context):
	context.no_cache = 1
	context.title = "Now Showing Movies"

	selected_genre = frappe.form_dict.get("genre")
	selected_language = frappe.form_dict.get("language")

	filters = {"movie_status": "Now Showing"}
	if selected_genre:
		filters["genre"] = selected_genre
	if selected_language:
		filters["language"] = selected_language

	context.movies = frappe.get_all(
		"Movie",
		filters=filters,
		fields=["name", "title", "slug", "language", "genre", "rating", "duration_minutes", "poster", "synopsis"],
		order_by="title asc"
	)

	context.genres = frappe.get_all("Movie Genre", filters={"is_active": 1}, pluck="name", order_by="genre_name asc")
	context.languages = ["English", "Hindi", "Gujarati", "Tamil", "Telugu", "Other"]
	context.selected_genre = selected_genre
	context.selected_language = selected_language
