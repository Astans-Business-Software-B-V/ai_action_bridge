# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Astans Business Software B.V.

from frappe.model.document import Document


class AIAction(Document):
	def on_update(self):
		refresh_assistant_tools()

	def on_trash(self):
		refresh_assistant_tools()


def refresh_assistant_tools():
	"""Refresh Frappe Assistant Core's tool registry.

	The dispatcher tool builds its description and input schema from the AI Action
	records when it is loaded, so the registry has to reload it after a change.
	Connected clients still need to reconnect to pick up the new description.
	"""
	try:
		from frappe_assistant_core.core.tool_registry import get_tool_registry

		get_tool_registry().refresh()
	except Exception:
		# A failing refresh must never block saving or deleting an action.
		pass
