# AI Action Bridge

Expose Frappe Server Scripts as MCP tools through
[Frappe Assistant Core](https://github.com/buildswithpaul/Frappe_Assistant_Core).
Define AI actions as records, no app code required.

AI Action Bridge is an independent app. It is not affiliated with or endorsed by
Frappe Technologies or the authors of Frappe Assistant Core.

## What it does

Frappe Assistant Core (FAC) turns a Frappe site into an MCP server. Adding a tool
to it normally means writing a Python class in an app and deploying that app.

This app adds one generic tool, `ai_action`, and a DocType, **AI Action**. Each
AI Action record describes one action the assistant may run and points to a
Server Script that does the work. The tool lists the enabled actions in its
description and dispatches a call to the matching script.

Adding an assistant capability to a site then takes two records:

1. a **Server Script** of type *API* with the logic;
2. an **AI Action** that names it, describes it for the assistant and optionally
   restricts it to certain roles.

## Requirements

- Frappe Framework 16
- Frappe Assistant Core, with its *Custom Tools* plugin enabled
- Server Scripts enabled on the site (`server_script_enabled` in the site config)

## Installation

```bash
bench get-app https://github.com/Astans-Business-Software-B-V/ai_action_bridge --branch <tag>
bench --site <site> install-app ai_action_bridge
```

## The Server Script contract

| | |
|---|---|
| Input | The `arguments` object of the tool call is available as `frappe.form_dict`. |
| Output | The script assigns a dict to `frappe.flags.ai_result`. |

Example Server Script (type *API*):

```python
item_code = frappe.form_dict.get("item_code")
if not item_code:
    frappe.throw("item_code is required")

frappe.flags.ai_result = {
    "item_code": item_code,
    "stock_uom": frappe.db.get_value("Item", item_code, "stock_uom"),
}
```

The matching AI Action:

| Field | Value |
|---|---|
| Action Name | `get_item_uom` |
| Server Script | the script above |
| Description | Returns the stock unit of measure of an item. |
| Parameters (JSON) | `{"item_code": "string, required"}` |

The assistant then calls the tool as:

```json
{"action": "get_item_uom", "arguments": {"item_code": "ITEM-0001"}}
```

Things to know:

- The script runs in Frappe's `safe_exec` sandbox, as the user who is connected to
  the assistant. It gets no extra permissions from this app; check permissions in
  the script where the action needs them.
- **Allowed Roles** on the AI Action limits who may run it. Empty means every user
  who can use the tool.
- An exception in the script is returned to the assistant as an error message.
- After adding or changing an AI Action, MCP clients have to reconnect to see the
  new tool description.

## Source code

This program is free software, released under the GNU Affero General Public
License, version 3 or (at your option) any later version. See [LICENSE](LICENSE).

The complete source code of the version running on a site is available at
<https://github.com/Astans-Business-Software-B-V/ai_action_bridge>; the installed
version (see the site's *About* dialog) corresponds to the release tag with the
same number.

Copyright (C) 2026 Astans Business Software B.V.
