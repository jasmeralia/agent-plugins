#!/usr/bin/env python3
"""PreToolUse hook: warn when a Jira sub-task is being filed at P2.

Some on-call ticket-filing workflows hardcode priority P2 as boilerplate in
their template, and it has been missed more than once - each time requiring
a manual downgrade to P3 after noticing the alert was actually low-urgency
(severity: warning, auto-resolving, non-customer-impacting, or similar).
This is a reminder, not a hard block - P2 is sometimes the right call for a
genuinely active/customer-impacting incident - but it forces a second look
every time P2 is about to be set.
"""
import json
import sys


def _priority_name(fields):
    if not isinstance(fields, dict):
        return None
    priority = fields.get("priority")
    if isinstance(priority, dict):
        return priority.get("name")
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        sys.exit(0)  # fail open - never block on a hook-input parsing issue

    tool_name = payload.get("tool_name", "")
    if not (tool_name.endswith("jira_create_issue") or tool_name.endswith("jira_update_issue")):
        sys.exit(0)

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        sys.exit(0)

    raw = tool_input.get("additional_fields") if tool_name.endswith("jira_create_issue") else tool_input.get("fields")
    if not isinstance(raw, str):
        sys.exit(0)

    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        sys.exit(0)

    if _priority_name(parsed) != "P2":
        sys.exit(0)

    message = (
        "HOOK REMINDER: this sub-task is about to be filed as P2. The "
        "standing rule is to default LOW-URGENCY incidents to P3 instead - "
        "check the alert's severity label, whether it auto-resolves vs. stays "
        "open/stuck, and whether there's actual customer impact before "
        "keeping P2. Not a hard block: if this really is an active, "
        "customer-impacting incident, P2 is correct - just confirm that "
        "first."
    )
    print(json.dumps({
        "systemMessage": message,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        },
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
