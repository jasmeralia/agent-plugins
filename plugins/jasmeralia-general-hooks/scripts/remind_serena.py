#!/usr/bin/env python3
"""PreToolUse hook: direct code search and discovery to Serena when suitable."""
import json
import sys


MESSAGES = {
    "Grep": (
        "HOOK REMINDER: Serena MCP is available. Prefer "
        "mcp__serena__search_for_pattern or mcp__serena__find_symbol over Grep "
        "unless searching non-code files (logs, CSVs, raw text)."
    ),
    "Glob": (
        "HOOK REMINDER: Serena MCP is available. Prefer mcp__serena__find_file "
        "or mcp__serena__list_dir over Glob unless Serena is not applicable."
    ),
}


def main():
    """Emit the matching advisory without blocking the requested search."""
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        return 0

    message = MESSAGES.get(payload.get("tool_name"))
    if message is None:
        return 0

    print(json.dumps({
        "systemMessage": message,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        },
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
