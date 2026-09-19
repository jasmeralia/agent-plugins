#!/usr/bin/env python3
"""PreToolUse hook: block smart quotes/en-dashes/em-dashes/NBSP in repo file writes.

Typography in code, scripts, and repo files: never use smart/curly quotes, en
dashes, em dashes, or non-breaking spaces in source files that live in a git
repo - code, scripts, config, README/docs, etc. Use plain ASCII instead.

Having that rule as text-only guidance does not reliably prevent slips (e.g.
a stray em dash landing in source that a repo's own lint step - such as a
"smart quote check" run as part of the test suite - greps for and fails the
build on), so this hook enforces it mechanically instead of relying on the
model to self-check every write.

Scope: only files that live inside a git repository (walks up from the
target path looking for a .git dir/file, so worktrees count too). Anything
outside a repo - scratchpad files, memory notes not under a repo, etc. - is
left alone, matching the rule's own scope ("any file that lives in a git
repo").

Deliberately does NOT cover commit messages or PR titles/descriptions - those
are created via Bash (`git commit`) or MCP/gh tools, never via Write/Edit, so
they never reach this hook. Commit messages aren't linted this way and don't
carry the same failure mode, so flagging them would be scope creep.

This is a hard block (exit 2), not a reminder: unlike the pronoun/priority
style hooks, there is no legitimate case where a repo source file should
contain these characters, so there is nothing to weigh - just fix it and
retry.
"""
import json
import os
import sys

FORBIDDEN = {
    "‘": "left curly single quote (use ')",
    "’": "right curly single quote/apostrophe (use ')",
    "“": "left curly double quote (use \")",
    "”": "right curly double quote (use \")",
    "–": "en dash (use - or \" - \")",
    "—": "em dash (use - or \" - \")",
    " ": "non-breaking space (use a normal space)",
}


def _is_inside_git_repo(file_path):
    path = os.path.abspath(os.path.dirname(file_path))
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return True
        parent = os.path.dirname(path)
        if parent == path:
            return False
        path = parent


def _extract_text(tool_name, tool_input):
    if tool_name.endswith("Write"):
        return tool_input.get("content")
    if tool_name.endswith("Edit"):
        # NotebookEdit uses new_source; plain Edit uses new_string.
        if "new_source" in tool_input:
            return tool_input.get("new_source")
        return tool_input.get("new_string")
    return None


def _find_violations(text):
    violations = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for ch in line:
            if ch in FORBIDDEN:
                violations.append((lineno, ch, FORBIDDEN[ch], line.strip()))
        if len(violations) >= 20:
            break
    return violations


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

    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        sys.exit(0)

    try:
        if not _is_inside_git_repo(file_path):
            sys.exit(0)
    except Exception:
        sys.exit(0)  # fail open - a bug in the hook must never block real work

    text = _extract_text(tool_name, tool_input)
    if not isinstance(text, str):
        sys.exit(0)

    try:
        violations = _find_violations(text)
    except Exception:
        sys.exit(0)

    if not violations:
        sys.exit(0)

    lines = [
        "BLOCKED: this write introduces smart quotes/en-dash/em-dash/non-breaking "
        f"space into a repo file ({file_path}).",
        "",
    ]
    for lineno, ch, desc, snippet in violations:
        lines.append(f"- line {lineno}: {desc} - {snippet!r}")
    if len(violations) >= 20:
        lines.append("- ... (more matches not shown)")
    lines.append("")
    lines.append(
        "This does not apply to commit messages or PR titles/descriptions - "
        "only to the actual file content. Replace with plain ASCII and retry."
    )

    print("\n".join(lines), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
