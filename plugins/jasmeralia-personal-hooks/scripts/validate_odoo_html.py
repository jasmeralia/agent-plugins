#!/usr/bin/env python3
"""PreToolUse hook: reject Odoo chatter HTML that Odoo would render as text."""
import json
import re
import sys


ESCAPED_TAG_RE = re.compile(
    r"&(?:lt|#0*60|#x0*3c);\s*/?\s*[a-z][a-z0-9:_-]*"
    r"(?:\s|&(?:gt|#0*62|#x0*3e);|>|/)",
    re.IGNORECASE,
)
HTML_TAG_RE = re.compile(r"</?[a-z][a-z0-9:_-]*(?:\s[^<>]*)?/?>", re.IGNORECASE)


def _post_message_fields(tool_input):
    """Return the Odoo MCP chatter body, if the call supplies one."""
    body = tool_input.get("body")
    if not isinstance(body, str) or not body.strip():
        return []
    return [("body", body, tool_input.get("body_is_html") is True, True)]


def _record_fields(tool_input):
    """Return HTML-capable fields for the Odoo generic record tools."""
    values = tool_input.get("values")
    if not isinstance(values, dict):
        return []

    model = tool_input.get("model")
    if model == "mail.message":
        body = values.get("body")
        if isinstance(body, str) and body.strip():
            # Odoo's native mail.message model accepts raw HTML directly. The
            # body_is_html flag belongs only to the Odoo MCP post_message tool.
            return [("values.body", body, True, False)]
    elif model == "project.task":
        description = values.get("description")
        if isinstance(description, str) and description.strip():
            return [("values.description", description, True, False)]
    return []


EXTRACTORS = {
    "mcp__odoo__post_message": _post_message_fields,
    "mcp__odoo__create_record": _record_fields,
    "mcp__odoo__update_record": _record_fields,
}


def snippet_around(text, start, end, pad=25):
    """Return a short printable excerpt surrounding a matched error."""
    lo, hi = max(0, start - pad), min(len(text), end + pad)
    excerpt = text[lo:hi].replace("\n", "\\n")
    return ("..." if lo else "") + excerpt + ("..." if hi < len(text) else "")


def find_violations(label, body, html_mode, requires_html_mode):
    """Find only Odoo rendering mistakes confirmed to show raw markup."""
    violations = []

    if requires_html_mode and not html_mode:
        violations.append((
            "missing-body-is-html",
            label,
            "body_is_html is not true",
            "Set body_is_html: true. mcp__odoo__post_message otherwise treats "
            "literal tags as text.",
        ))

    for match in ESCAPED_TAG_RE.finditer(body):
        violations.append((
            "escaped-html-tag",
            label,
            snippet_around(body, match.start(), match.end()),
            "Use literal <tag> markup, never &lt;tag&gt; or a numeric HTML "
            "entity. Odoo does not decode the entity before rendering.",
        ))

    if requires_html_mode and not HTML_TAG_RE.search(body):
        violations.append((
            "non-html-chatter-body",
            label,
            snippet_around(body, 0, min(len(body), 50)),
            "Send an HTML body such as <p>Comment text</p>; do not send raw "
            "Markdown or plain text to Odoo chatter.",
        ))

    return violations


def main():
    """Validate applicable Odoo MCP calls, failing open on malformed input."""
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        return 0

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input")
    extractor = EXTRACTORS.get(tool_name)
    if extractor is None or not isinstance(tool_input, dict):
        return 0

    try:
        fields = extractor(tool_input)
    except Exception:
        return 0

    violations = []
    for label, body, html_mode, requires_html_mode in fields:
        violations.extend(find_violations(label, body, html_mode, requires_html_mode))

    if not violations:
        return 0

    lines = [
        f"BLOCKED: Odoo HTML rendering issue(s) detected before sending to {tool_name}.",
        "Odoo chatter must receive literal HTML, not escaped tags or Markdown.",
        "",
    ]
    for rule, label, snippet, fix in violations:
        lines.append(f"- [{rule}] in `{label}`: {snippet!r}")
        lines.append(f"  Fix: {fix}")
    lines.extend((
        "",
        "For mcp__odoo__post_message, use literal HTML with body_is_html: true.",
        "For generic mail.message create/update calls, put literal HTML directly in "
        "values.body; body_is_html is not a native mail.message field.",
        "Fix the body and retry the call.",
    ))
    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
