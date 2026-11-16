# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Astans Business Software B.V.

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from ai_action_bridge.tools.action_tool import TOOL_NAME, AIActionTool

SCRIPT_NAME = "AI Action Bridge Test Echo"
ACTION_NAME = "bridge_test_echo"

# Echoes its input, so the test can check both halves of the Server Script contract.
SCRIPT_BODY = "frappe.flags.ai_result = {'echo': frappe.form_dict.get('value')}"


class TestAIAction(IntegrationTestCase):
	def setUp(self):
		# Server Scripts are switched off by default; the bridge depends on them.
		self._server_script_enabled = frappe.conf.get("server_script_enabled")
		frappe.conf.server_script_enabled = 1

		if not frappe.db.exists("Server Script", SCRIPT_NAME):
			frappe.get_doc(
				{
					"doctype": "Server Script",
					"name": SCRIPT_NAME,
					"script_type": "API",
					"api_method": "ai_action_bridge_test_echo",
					"script": SCRIPT_BODY,
				}
			).insert()

	def tearDown(self):
		frappe.conf.server_script_enabled = self._server_script_enabled
		# Every test starts without the test action and scripts of the previous one.
		frappe.db.rollback()

	def make_action(self, **overrides):
		values = {
			"doctype": "AI Action",
			"action_name": ACTION_NAME,
			"title": "Echo",
			"description": "Returns the given value.",
			"server_script": SCRIPT_NAME,
			"enabled": 1,
		}
		values.update(overrides)
		return frappe.get_doc(values).insert()

	def test_tool_identity(self):
		tool = AIActionTool()
		self.assertEqual(tool.name, TOOL_NAME)
		self.assertEqual(tool.name, "ai_action")
		self.assertEqual(tool.source_app, "ai_action_bridge")

	def test_tool_is_registered_through_the_hook(self):
		self.assertIn(
			"ai_action_bridge.tools.action_tool.AIActionTool", frappe.get_hooks("assistant_tools")
		)

	def test_description_and_schema_follow_the_actions(self):
		self.assertNotIn(ACTION_NAME, AIActionTool().description)

		self.make_action(parameters='{"value": "string"}')
		tool = AIActionTool()
		self.assertIn(f"`{ACTION_NAME}`: Returns the given value.", tool.description)
		self.assertIn('arguments: {"value": "string"}', tool.description)
		self.assertIn(ACTION_NAME, tool.inputSchema["properties"]["action"]["enum"])
		self.assertEqual(tool.inputSchema["required"], ["action"])

	def test_disabled_action_is_not_offered(self):
		self.make_action(enabled=0)
		tool = AIActionTool()
		self.assertNotIn(ACTION_NAME, tool.description)

		result = tool.execute({"action": ACTION_NAME})
		self.assertFalse(result["success"])
		self.assertIn("Unknown or disabled action", result["error"])

	def test_missing_and_unknown_action(self):
		tool = AIActionTool()
		self.assertFalse(tool.execute({})["success"])

		result = tool.execute({"action": "does_not_exist"})
		self.assertFalse(result["success"])
		self.assertIn("Unknown or disabled action", result["error"])

	def test_dispatch_passes_arguments_and_returns_the_result(self):
		self.make_action()
		form_dict_before = frappe.local.form_dict

		result = AIActionTool().execute({"action": ACTION_NAME, "arguments": {"value": 42}})

		self.assertEqual(result, {"success": True, "result": {"echo": 42}})
		# The dispatcher restores the request's own form_dict afterwards.
		self.assertIs(frappe.local.form_dict, form_dict_before)

	def test_script_error_is_reported_not_raised(self):
		frappe.get_doc(
			{
				"doctype": "Server Script",
				"name": SCRIPT_NAME + " Failing",
				"script_type": "API",
				"api_method": "ai_action_bridge_test_failing",
				"script": "frappe.throw('nope')",
			}
		).insert()
		self.make_action(server_script=SCRIPT_NAME + " Failing")

		result = AIActionTool().execute({"action": ACTION_NAME})
		self.assertFalse(result["success"])
		self.assertIn("failed", result["error"])

	def test_allowed_roles_restrict_access(self):
		self.make_action(allowed_roles=[{"role": "System Manager"}])
		tool = AIActionTool()

		with patch("frappe.get_roles", return_value=["Guest"]):
			result = tool.execute({"action": ACTION_NAME, "arguments": {"value": 1}})
		self.assertFalse(result["success"])
		self.assertIn("No access", result["error"])

		with patch("frappe.get_roles", return_value=["System Manager"]):
			result = tool.execute({"action": ACTION_NAME, "arguments": {"value": 1}})
		self.assertTrue(result["success"])

	def test_saving_and_deleting_refresh_the_registry(self):
		target = "ai_action_bridge.ai_action_bridge.doctype.ai_action.ai_action.refresh_assistant_tools"
		with patch(target) as refresh:
			action = self.make_action()
			self.assertEqual(refresh.call_count, 1)
			action.delete()
			self.assertEqual(refresh.call_count, 2)
