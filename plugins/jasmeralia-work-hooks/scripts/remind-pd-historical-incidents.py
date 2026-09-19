#!/usr/bin/env python3
"""PreToolUse hook: warn that get_past_incidents/get_related_incidents 403s."""
import json

MESSAGE = (
    "HOOK REMINDER: this tool requires the PagerDuty Event Intelligence / "
    "Digital Operations add-on, which may not be enabled on every account - "
    "it will return 403 Access Denied if it isn't. Do not retry expecting a "
    "different result; there is no historical-similarity or related-"
    "incidents data available without that add-on. Use a local PagerDuty "
    "REST API script for historical/related-incident questions instead. If "
    "you have more than one PagerDuty account/org configured, double check "
    "which one this call is scoped to."
)

print(json.dumps({
    "systemMessage": MESSAGE,
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": MESSAGE,
    },
}))
