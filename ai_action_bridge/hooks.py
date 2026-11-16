# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Astans Business Software B.V.

app_name = "ai_action_bridge"
app_title = "AI Action Bridge"
app_publisher = "Astans Business Software B.V."
app_description = (
	"Expose Frappe Server Scripts as MCP tools through Frappe Assistant Core. "
	"Define AI actions as records, no app code required. "
	"Source: https://github.com/Astans-Business-Software-B-V/ai_action_bridge"
)
app_email = "info@astans.nl"
app_license = "AGPL-3.0-or-later"

# The bridge only makes sense next to Frappe Assistant Core: it registers one tool with it.
required_apps = ["frappe_assistant_core"]

# Frappe Assistant Core discovers external tools through this hook.
assistant_tools = ["ai_action_bridge.tools.action_tool.AIActionTool"]
