#!/usr/bin/env python3
"""PreToolUse hook: warn about list_incidents scoping/filter gaps."""
import json

MESSAGE = (
    "HOOK REMINDER: list_incidents pulls the fleet-wide PagerDuty incident "
    "feed and gets capped/truncated on multi-week windows. A service_ids (or "
    "similar) filter is silently IGNORED by this tool - it accepts the param "
    "without erroring but returns unrelated services anyway, so never trust "
    "it worked without checking the response. request_scope=assigned only "
    "reflects CURRENTLY-open incidents - the assignments array comes back "
    "empty for anything already resolved, so it undercounts any \"how many "
    "incidents paged me\" question. For scoped/historical questions, use a "
    "local PagerDuty REST API script instead (properly scoped, e.g. by "
    "--service/--escalation-policy/--pattern/--days) rather than this tool. "
    "If you have more than one PagerDuty account/org configured, double "
    "check which one the call is scoped to before trusting the result."
)

print(json.dumps({
    "systemMessage": MESSAGE,
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": MESSAGE,
    },
}))
