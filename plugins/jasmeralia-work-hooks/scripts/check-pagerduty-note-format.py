#!/usr/bin/env python3
"""PreToolUse hook: enforce the "WI: <url>" PagerDuty note format.

PagerDuty incident notes created via add_note_to_incident in this workflow
are always meant to be the work-item backlink in exactly this form (a note
with an appended parenthetical explanation has been a confirmed violation
before); enforce it mechanically instead of relying on remembering the
convention each time.
"""
import json
import re
import sys

WI_NOTE_RE = re.compile(r"^WI: https?://\S+$")


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        sys.exit(0)  # fail open - never block on a hook-input parsing issue

    tool_name = payload.get("tool_name", "")
    if not tool_name.endswith("add_note_to_incident"):
        sys.exit(0)

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        sys.exit(0)

    note = tool_input.get("note")
    if not isinstance(note, str):
        sys.exit(0)

    if WI_NOTE_RE.match(note.strip()):
        sys.exit(0)

    print(
        "BLOCKED: PagerDuty incident notes must be formatted as exactly "
        "\"WI: <url>\" with nothing else appended.\n"
        f"Got: {note!r}\n"
        "Put any additional context (recurrence details, root-cause "
        "summary, etc.) in the Jira comment instead, not in the PagerDuty "
        "note. Fix the note text and retry.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
