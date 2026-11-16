# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Astans Business Software B.V.

"""
AIActionTool: one generic MCP tool that dispatches to site-configured AI Actions.

Frappe Assistant Core loads this tool through the `assistant_tools` hook. Its
description and input schema are built from the "AI Action" records on the site.
Each action points to a Server Script (type API) that does the actual work, so a
site can add assistant capabilities with configuration and a Server Script
instead of app code.

Contract with the Server Script:
- Input : the dispatcher puts the given `arguments` on `frappe.form_dict` for the
          duration of the call. The script reads its input there, e.g.
          `frappe.form_dict.get("item_code")`.
- Output: the script puts its result (a dict) on `frappe.flags.ai_result`.
"""

import frappe
from frappe_assistant_core.core.base_tool import BaseTool

TOOL_NAME = "ai_action"

_INTRO = "Runs an action that is configured on this site."


class AIActionTool(BaseTool):
	"""Dispatcher tool: runs a configured AI Action through its Server Script."""

	def __init__(self):
		super().__init__()
		self.name = TOOL_NAME
		self.source_app = "ai_action_bridge"
		self.category = "Custom"
		self.requires_permission = None  # access is decided per action, through its allowed roles

		actions = self._load_actions()
		self.description = self._build_description(actions)
		self.inputSchema = self._build_input_schema(actions)

	# ---- loading the configuration (defensive: must never raise) ----------

	@staticmethod
	def _load_actions():
		try:
			if not getattr(frappe, "db", None) or not frappe.db.table_exists("AI Action"):
				return []
			return frappe.get_all(
				"AI Action",
				filters={"enabled": 1},
				fields=["name", "action_name", "title", "description", "parameters"],
				order_by="action_name asc",
			)
		except Exception:
			return []

	def _build_description(self, actions):
		if not actions:
			return f"{_INTRO} No actions are configured at the moment."
		lines = [
			f"{_INTRO} Call it with `action` (one of the actions below) and `arguments` "
			"(the fields that belong to that action). Available actions:"
		]
		for a in actions:
			lines.append(f"\n- `{a.action_name}`: {(a.description or a.title or '').strip()}")
			if a.parameters:
				lines.append(f"\n    arguments: {a.parameters.strip()}")
		return "".join(lines)

	def _build_input_schema(self, actions):
		action_prop = {
			"type": "string",
			"description": "The action to run (see the tool description for the options and their arguments).",
		}
		names = [a.action_name for a in actions if a.action_name]
		if names:
			action_prop["enum"] = names
		return {
			"type": "object",
			"properties": {
				"action": action_prop,
				"arguments": {
					"type": "object",
					"description": "Arguments for the chosen action.",
				},
			},
			"required": ["action"],
		}

	# ---- running an action -------------------------------------------------

	def execute(self, arguments):
		arguments = arguments or {}
		action_name = arguments.get("action")
		action_args = arguments.get("arguments") or {}

		if not action_name:
			return {"success": False, "error": "Specify an 'action'."}

		action = self._get_action(action_name)
		if not action:
			available = ", ".join(a.action_name for a in self._load_actions()) or "(none)"
			return {
				"success": False,
				"error": f"Unknown or disabled action '{action_name}'. Available: {available}.",
			}

		if not self._role_allowed(action):
			return {"success": False, "error": f"No access to action '{action_name}'."}

		return self._run_server_script(action, action_args)

	@staticmethod
	def _get_action(action_name):
		# The document name equals action_name (autoname field:action_name).
		try:
			doc = frappe.get_doc("AI Action", action_name)
		except Exception:
			return None
		return doc if doc.enabled else None

	@staticmethod
	def _role_allowed(action):
		roles = [r.role for r in (action.allowed_roles or [])]
		if not roles:
			return True
		return bool(set(roles) & set(frappe.get_roles(frappe.session.user)))

	@staticmethod
	def _run_server_script(action, action_args):
		if not action.server_script:
			return {"success": False, "error": f"Action '{action.action_name}' has no Server Script."}

		original_form_dict = getattr(frappe.local, "form_dict", None)
		try:
			frappe.local.form_dict = frappe._dict(action_args or {})
			script = frappe.get_doc("Server Script", action.server_script)
			flags = script.execute_method() or {}
			result = flags.get("ai_result") if hasattr(flags, "get") else None
			if result is None:
				return {"success": True, "result": {"message": "Action completed."}}
			return {"success": True, "result": result}
		except frappe.PermissionError:
			raise
		except Exception as e:
			return {"success": False, "error": f"Server Script '{action.server_script}' failed: {e}"}
		finally:
			frappe.local.form_dict = original_form_dict
