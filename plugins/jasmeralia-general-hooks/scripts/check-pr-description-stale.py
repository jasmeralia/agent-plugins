#!/usr/bin/env python3
"""PostToolUse hook: remind to reconcile the PR description after a git push.

Fires after a successful `git push` and, if the current branch has an open
PR, reminds the agent to double check that the PR description/summary and
test-plan checklist still match what was just pushed. Advisory only - it
cannot tell whether the description actually IS stale, just that a push
just happened and is worth checking against it.
"""
import json
import subprocess
import sys


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        sys.exit(0)  # fail open - never block on a hook-input parsing issue

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        sys.exit(0)

    command = tool_input.get("command")
    if not isinstance(command, str) or "git push" not in command:
        sys.exit(0)

    tool_response = payload.get("tool_response")
    if isinstance(tool_response, dict) and tool_response.get("success") is False:
        sys.exit(0)  # the push itself failed - nothing to reconcile

    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "number,url"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        sys.exit(0)

    if result.returncode != 0:
        sys.exit(0)  # no open PR for this branch (or gh/git unavailable)

    try:
        pr = json.loads(result.stdout)
        number = pr["number"]
        url = pr["url"]
    except (ValueError, KeyError, TypeError):
        sys.exit(0)

    message = (
        f"HOOK REMINDER: that push landed on branch with open PR #{number} "
        f"({url}). Check whether the PR description's summary and test-plan "
        "checklist still match what was just pushed - stale PR descriptions "
        "are easy to miss after follow-up commits."
    )
    print(json.dumps({
        "systemMessage": message,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": message,
        },
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
