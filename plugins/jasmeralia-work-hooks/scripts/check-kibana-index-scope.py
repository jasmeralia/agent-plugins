#!/usr/bin/env python3
"""PreToolUse hook: block unscoped filebeat-* / filebeat-k8s-events-* Kibana
index wildcards before the Kibana search MCP tool.

Confirmed-real trap: `filebeat-*` matches every cluster's application logs
AND every cluster's k8s-events index, and a bare `filebeat-k8s-events-*`
matches every cluster's events with no date bound. Both silently return
fleet-wide results with no error when the caller meant one cluster - an
on-call investigation querying `filebeat-*` intending to search one
cluster's logs could just as easily silently mix in a same-named pod from a
different cluster with no error to flag it.

Scoped patterns (`filebeat-<cluster>-*`, `filebeat-k8s-events-<cluster>-*`,
or a dated fleet sweep like `filebeat-k8s-events-*-<date>`) all pass through
untouched - only the two bare, cluster-less forms are blocked.
"""
import json
import re
import sys

UNSCOPED_RE = re.compile(r"^filebeat(-k8s-events)?-\*$")


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        sys.exit(0)  # fail open - never block on a hook-input parsing issue

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        sys.exit(0)

    index = tool_input.get("index")
    if not isinstance(index, str):
        sys.exit(0)

    parts = [p.strip() for p in index.split(",") if p.strip()]
    bad = [p for p in parts if UNSCOPED_RE.match(p)]
    if not bad:
        sys.exit(0)

    tool_name = payload.get("tool_name", "the Kibana search tool")
    lines = [
        f"BLOCKED: unscoped Kibana index wildcard before {tool_name}.",
        "",
    ]
    for p in bad:
        lines.append(
            f"- `{p}` matches every cluster in the fleet, not just the one "
            "you intend - a same-named pod/namespace on another cluster "
            "would silently pollute the results with no error."
        )
    lines.append("")
    lines.append(
        "Fix: scope to a cluster, e.g. `filebeat-<cluster>-*` (application "
        "logs) or `filebeat-k8s-events-<cluster>-*` (k8s events). If a "
        "fleet-wide sweep is genuinely intended, scope by date instead, "
        "e.g. `filebeat-k8s-events-*-<YYYY-MM-DD>` - never a bare unscoped "
        "wildcard with no cluster or date segment."
    )

    print("\n".join(lines), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
