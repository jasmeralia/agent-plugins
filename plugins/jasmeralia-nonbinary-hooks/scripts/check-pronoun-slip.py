#!/usr/bin/env python3
"""PreToolUse hook: warn on gendered pronouns in low-scrutiny written artifacts.

This plugin exists because the people it was built to protect - Jasmeralia,
Morgan, and Nathan - all use they/them, and a gendered pronoun slip has
landed in durable written artifacts (a memory note, a hook docstring) more
than once despite that being known context throughout. Both real slips
happened in low-scrutiny prose, not in direct conversation - exactly the gap
a mechanical hook can close that relying on the model to self-check cannot.

Assumption: if you're installing this plugin, you (and/or the people you
write about in your own memory/hook files) are also nonbinary and want the
same mechanical backstop, rather than a name-matching check tuned to one
specific roster. The regex below is deliberately identity-agnostic - it
flags any gendered pronoun in the scoped paths below, regardless of who the
text is about, and leaves it to you to judge whether the hit is a real slip
about someone in your own roster or a quoted third party's own pronouns.

Scoped to a user's memory directory and hook scripts, since that is where
the real slips happened; a blanket repo-wide scan would false-positive on
quoted third-party text (e.g. a Slack message quoting someone else's "she").
"""
import json
import re
import sys

PRONOUN_RE = re.compile(r"\b(he|him|his|himself|she|her|hers|herself)\b", re.IGNORECASE)

SCOPED_PATH_SUBSTRINGS = (
    "/.claude/hooks/",
    "/memory/",
)


def _extract_text(tool_name, tool_input):
    if tool_name.endswith("Write"):
        return tool_input.get("content")
    if tool_name.endswith("Edit"):
        return tool_input.get("new_string")
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        sys.exit(0)  # fail open - never block on a hook-input parsing issue

    tool_name = payload.get("tool_name", "")
    if not (tool_name.endswith("Write") or tool_name.endswith("Edit")):
        sys.exit(0)

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not isinstance(file_path, str) or not any(s in file_path for s in SCOPED_PATH_SUBSTRINGS):
        sys.exit(0)

    text = _extract_text(tool_name, tool_input)
    if not isinstance(text, str):
        sys.exit(0)

    matches = sorted({m.group(0).lower() for m in PRONOUN_RE.finditer(text)})
    if not matches:
        sys.exit(0)

    message = (
        "HOOK REMINDER: gendered pronoun(s) "
        + ", ".join(matches)
        + f" found in this write to {file_path}. If this text refers to "
        "someone in your nonbinary roster (they/them), fix it before saving. "
        "Slips like this have landed twice before in exactly this kind of "
        "low-scrutiny prose (a memory note, a hook docstring); if this is a "
        "quoted third party's own pronouns, ignore this reminder."
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
