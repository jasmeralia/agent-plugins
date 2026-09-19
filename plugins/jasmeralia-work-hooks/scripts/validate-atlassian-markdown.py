#!/usr/bin/env python3
"""PreToolUse hook: catch confirmed-real markdown bugs before mcp-atlassian writes.

Confirmed-real bugs (each caught in production tickets, not hypothetical):
  1. Bare URLs outside markdown link syntax [text](url).
  2. A parenthesis touching a code-span backtick with no space: (`x` or `x`).
  3. Broken @mention syntax - three different wrong forms have each been
     used at least once in real tickets (all render as dead, unlinked
     literal text, not a notifying mention):
       - `User:ACCOUNT_ID` (no brackets/tilde at all)
       - `[~ACCOUNT_ID]` (bare, no `accountid:` label)
       - `[~email@domain]`
     The only confirmed-working form is `[~accountid:ACCOUNT_ID]`.
  4. A **bold** span that contains a markdown link, or a bare Jira issue
     key (e.g. PROJ-1234), gets corrupted on write - Jira auto-links
     recognized issue keys in plain text *after* markdown conversion, and
     that injected link corrupts an enclosing bold span the same way an
     explicit link does. Keep bold text free of both issue keys and
     markdown links; put the key/link outside the bold run.

Deliberately does NOT flag underscores/asterisks inside inline code or fenced
code blocks - that's a confirmed false alarm, not a real bug.

Matchers reference both a generic `mcp-atlassian` server name and a
second-account variant - adjust these to match whatever Atlassian MCP
server(s) you actually have installed.
"""
import json
import re
import sys

# tool_name (short form, after the mcp__<server>__ prefix) -> how to pull the
# markdown text field(s) out of tool_input. Each extractor returns a list of
# (label, text) pairs to check.

def _jira_create_issue(ti):
    d = ti.get("description")
    return [("description", d)] if isinstance(d, str) else []


def _jira_update_issue(ti):
    raw = ti.get("fields")
    if not isinstance(raw, str):
        return []
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if isinstance(parsed, dict) and isinstance(parsed.get("description"), str):
        return [("fields.description", parsed["description"])]
    return []


def _body_field(ti):
    b = ti.get("body")
    return [("body", b)] if isinstance(b, str) else []


def _confluence_page_content(ti):
    fmt = ti.get("content_format") or "markdown"
    c = ti.get("content")
    if fmt == "markdown" and isinstance(c, str):
        return [("content", c)]
    return []


def _confluence_update_page_section(ti):
    fmt = ti.get("content_format") or "markdown"
    c = ti.get("new_content")
    if fmt == "markdown" and isinstance(c, str):
        return [("new_content", c)]
    return []


EXTRACTORS = {
    "jira_create_issue": _jira_create_issue,
    "jira_update_issue": _jira_update_issue,
    "jira_add_comment": _body_field,
    "jira_edit_comment": _body_field,
    "confluence_add_comment": _body_field,
    "confluence_add_inline_comment": _body_field,
    "confluence_reply_to_comment": _body_field,
    "confluence_create_page": _confluence_page_content,
    "confluence_update_page": _confluence_page_content,
    "confluence_update_page_section": _confluence_update_page_section,
}

CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
# A bare URL not already the target of a markdown link, i.e. not preceded by "](".
BARE_URL_RE = re.compile(r"(?<!\]\()https?://[^\s\]\)\"'<>]+")
PAREN_BACKTICK_RE = re.compile(r"\(`|`\)")
# Broken @mention forms.
BAD_MENTION_USER_PREFIX_RE = re.compile(r"\bUser:[A-Za-z0-9:_-]+")
BAD_MENTION_BRACKET_RE = re.compile(r"\[~(?!accountid:)[^\]]*\]")
# A **bold** run, not crossing a paragraph break (blank line) or containing
# a nested "**" - see point 4 in the module docstring.
BOLD_SPAN_RE = re.compile(r"\*\*((?:(?!\*\*|\n\n).)+?)\*\*", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]+\)")
JIRA_ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d{1,6}\b")


def mask_code_fences(text):
    """Replace fenced code block contents with spaces (same length) so bare
    URLs / raw markup inside code fences are never checked, while match
    offsets still line up with the original text for snippet extraction."""
    return CODE_FENCE_RE.sub(lambda m: " " * len(m.group(0)), text)


def snippet_around(text, start, end, pad=25):
    lo, hi = max(0, start - pad), min(len(text), end + pad)
    s = text[lo:hi].replace("\n", "\\n")
    prefix = "..." if lo > 0 else ""
    suffix = "..." if hi < len(text) else ""
    return f"{prefix}{s}{suffix}"


def find_violations(label, text):
    violations = []
    masked = mask_code_fences(text)

    for m in BARE_URL_RE.finditer(masked):
        violations.append((
            "bare-url",
            label,
            snippet_around(text, m.start(), m.end()),
            "Wrap it in markdown link syntax: [label](%s)" % m.group(0),
        ))

    for m in PAREN_BACKTICK_RE.finditer(masked):
        violations.append((
            "paren-backtick-adjacency",
            label,
            snippet_around(text, m.start(), m.end()),
            "Add a space between the parenthesis and the backtick, "
            "e.g. \"( `code` )\" not \"(`code`)\".",
        ))

    for m in BAD_MENTION_USER_PREFIX_RE.finditer(masked):
        violations.append((
            "broken-mention-syntax",
            label,
            snippet_around(text, m.start(), m.end()),
            "\"User:ID\" renders as dead literal text, not a mention. "
            "Use [~accountid:ID] instead.",
        ))

    for m in BAD_MENTION_BRACKET_RE.finditer(masked):
        violations.append((
            "broken-mention-syntax",
            label,
            snippet_around(text, m.start(), m.end()),
            "A bare [~ID] or [~email] mention renders as dead literal text "
            "(the accountid: label is required). Use [~accountid:ID] instead.",
        ))

    for m in BOLD_SPAN_RE.finditer(masked):
        content = INLINE_CODE_RE.sub("", m.group(1))
        if MD_LINK_RE.search(content):
            violations.append((
                "bold-contains-link",
                label,
                snippet_around(text, m.start(), m.end()),
                "A markdown link inside **bold** gets corrupted (duplicated/"
                "nested brackets) on write. Move the link outside the bold "
                "span, e.g. \"**From** [X](url) **(text):**\" or drop the "
                "bold around it entirely.",
            ))
        if JIRA_ISSUE_KEY_RE.search(content):
            violations.append((
                "bold-contains-issue-key",
                label,
                snippet_around(text, m.start(), m.end()),
                "A bare issue key (e.g. PROJ-1234) inside **bold** gets "
                "corrupted: Jira auto-links the key after markdown "
                "conversion, and the injected link splits the enclosing "
                "** markers. Move the key outside the bold span, e.g. "
                "\"**Update:** ... PROJ-1234 ...\" not \"**Update: ... "
                "PROJ-1234 ...**\".",
            ))

    return violations


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        sys.exit(0)  # fail open - never block on a hook-input parsing issue

    tool_name = payload.get("tool_name", "")
    short_name = tool_name.rsplit("__", 1)[-1]
    tool_input = payload.get("tool_input")

    extractor = EXTRACTORS.get(short_name)
    if extractor is None or not isinstance(tool_input, dict):
        sys.exit(0)

    try:
        fields = extractor(tool_input)
    except Exception:
        sys.exit(0)  # fail open - a bug in the hook must never block real work

    all_violations = []
    for label, text in fields:
        all_violations.extend(find_violations(label, text))

    if not all_violations:
        sys.exit(0)

    lines = [
        "BLOCKED: markdown formatting issue(s) detected before sending to "
        f"{tool_name}.",
        "These are confirmed-real Jira/Confluence rendering bugs (not the "
        "underscore/asterisk-in-code-span false alarm - that one is fine "
        "and must not be flagged).",
        "",
    ]
    for rule, label, snippet, fix in all_violations:
        lines.append(f"- [{rule}] in `{label}`: {snippet!r}")
        lines.append(f"  Fix: {fix}")
    lines.append("")
    lines.append("Fix the text and retry the call.")

    print("\n".join(lines), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
