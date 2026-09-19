#!/usr/bin/env python3
"""PreToolUse hook: warn before transitioning a DEVOPS-project Jira issue.

Some Jira workflows have post-functions that change Assignee as a side
effect of certain transitions (e.g. reassigning to the first Code Reviewer
on a Code Review transition, unassigning on a Close transition). This is
intentional workflow behavior, not a bug - it has been "fixed" back
incorrectly at least once already. This is a reminder, not a hard block -
just don't revert an assignee change that this same transition call just
caused.

Adjust the `DEVOPS-` project-key prefix below to match whichever project(s)
in your own Jira instance have this kind of assignee-changing workflow.
"""
import json
import sys


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        sys.exit(0)  # fail open - never block on a hook-input parsing issue

    tool_name = payload.get("tool_name", "")
    if not tool_name.endswith("jira_transition_issue"):
        sys.exit(0)

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        sys.exit(0)

    issue_key = tool_input.get("issue_key")
    if not isinstance(issue_key, str) or not issue_key.startswith("DEVOPS-"):
        sys.exit(0)

    message = (
        "HOOK REMINDER: transitioning a DEVOPS-project Jira issue. The DEVOPS "
        "workflow has post-functions that change Assignee as a side effect of "
        "certain transitions - e.g. reassigning to the first Code Reviewer on "
        "the Code Review transition, or unassigning on a Close transition. "
        "This is intentional workflow behavior, not a bug - do not 'fix' the "
        "resulting assignee back to what it was before this transition."
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
