# Copyright (c) 2026, Abhijit P Dodiya and contributors
# For license information, please see license.txt

"""
================================================================================
CONCEPT DEMO: override_whitelisted_methods in Frappe Framework
================================================================================

Task 3.2 (B) Requirement:
- Create a wrapper around frappe.client.get_count that logs the DocType/filters
  being queried.
- Add a detailed comment block covering:
  1. Use Cases
  2. Risks & Caveats
  3. When to use vs Alternatives

1. USE CASES:
--------------------------------------------------------------------------------
- Telemetry & Performance Profiling:
  Track high-frequency query patterns, identify missing database indices on filter
  combinations, and measure API latency without altering application code.
- Dynamic Security Enforcement & Multi-Tenancy:
  Intercept standard framework APIs (e.g. frappe.client.get_count, frappe.client.get_list)
  to inject compulsory tenant filters, restrict access to sensitive DocTypes for
  external API keys, or implement strict rate limiting.
- Caching Layers:
  Cache frequently queried record counts (such as available tickets or active users)
  in Redis to prevent heavy SQL COUNT(*) operations on large tables.

2. RISKS & CAVEATS:
--------------------------------------------------------------------------------
- Upstream Compatibility Regressions:
  If a Frappe Framework update alters the signature, return type, or internal behavior
  of the whitelisted function, your override may fail, crash desk list views, or
  cause silent data inconsistencies.
- Performance Degeneration:
  Adding synchronous DB queries, external HTTP calls, or slow logging logic inside
  heavily used whitelisted methods directly impacts every desk interaction.
- Incomplete Coverage:
  Whitelisted method overrides ONLY intercept calls arriving via `/api/method/...`.
  They do NOT intercept direct Python calls, background workers, or standard server-side
  ORM queries (frappe.db.count).

3. WHEN TO USE VS ALTERNATIVES:
--------------------------------------------------------------------------------
- Use `override_whitelisted_methods`:
  ONLY when you need to intercept or modify built-in Frappe endpoints called directly
  by core Frappe Desk UI components (e.g., list views, search bars, dashboard cards)
  where the frontend route cannot be changed to a custom endpoint.
- Alternative 1: Custom Whitelisted Method (`@frappe.whitelist`):
  Preferred for all new frontend features, mobile apps, or custom integrations.
  Keeps business logic decoupled from framework internals.
- Alternative 2: Document Controller Hooks (`doc_events`):
  Preferred when validating, updating, or restricting document state. Doc events
  apply universally (Desk, REST API, Webhooks, Scheduler, Console).
- Alternative 3: Permission Query Conditions (`permission_query_conditions`):
  Preferred for restricting which records a user can read or count based on their
  role or territory.
================================================================================
"""

import frappe
import frappe.client


@frappe.whitelist()
def custom_get_count(
	doctype: str,
	filters: str | list | dict | None = None,
	debug: int | bool = False,
	cache: int | bool = False,
):
	"""Custom wrapper around frappe.client.get_count.

	Logs the DocType and filter criteria being queried before delegating to the core method.
	"""
	frappe.logger("movie_tickets").info(
		f"[AUDIT] frappe.client.get_count queried for DocType: '{doctype}', filters: {filters}"
	)

	# Delegate to core implementation
	return frappe.client.get_count(doctype=doctype, filters=filters, debug=debug, cache=cache)
