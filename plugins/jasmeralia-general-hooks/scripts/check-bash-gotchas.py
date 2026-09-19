#!/usr/bin/env python3
"""PreToolUse hook: catch documented zsh/shell gotchas before Bash executes them.

These are shell-scripting traps that are easy to write down once and still
forget under load. Having them as text-only guidance in a CLAUDE.md/AGENTS.md
file does not reliably prevent the mistake (that's usually why they get
written down in the first place - after the mistake already happened), so
this hook enforces them mechanically instead of relying on the model to
recall and self-check every time.

Checks (each independent, all fail-open on any internal error):
  1. `status=$(...)` / `status=`...`` - zsh reserves `status` as a read-only
     alias for `$?`; assigning to a bare variable literally named `status`
     fails immediately and silently kills whatever loop/script contained it.
  2. `rm `, `mv `, `cp ` invoked as the first word of a (sub)shell statement
     without a `command ` prefix - relevant if your shell config aliases
     these to their `-i` (interactive-confirm) form, which hangs waiting for
     a y/n that never arrives in a non-interactive tool call.
  3. Bare `htop` as the first word of a statement without a `command ` prefix
     - relevant if your shell config aliases it to `sudo /usr/bin/htop`, an
     implicit privilege escalation.
  4. `bash -n` used to "validate" a shell script - only checks parse syntax,
     misses real bugs; the documented replacement is `shellcheck`.

Checks 2 and 3 assume a zsh config that aliases rm/mv/cp/htop this way (a
common but not universal convention) - harmless no-ops if your shell doesn't
alias them, since the pattern just won't match anything worth flagging in
practice beyond the literal command text.

Only flags rm/mv/cp/htop when they start a fresh statement (right after `;`,
`&&`, `||`, `|`, a newline, `(`, or the start of the command string) - this
naturally excludes `git rm`, `npm rm`, `docker cp`, etc. (there's an
intervening word before the separator) and anything already prefixed with
`command `/`command_` since that would occupy the "first word" slot instead.
Known false-positive case, accepted deliberately: an `rm`/`mv`/`cp`/`htop`
token that appears as the first word *inside a quoted string* right after a
separator (e.g. `echo 'do it now; rm -rf /tmp'`) - this hook does not parse
shell quoting. A false positive here just means re-running the same command;
the risk being guarded against (a silent hang) is worse than that friction.
"""
import re
import sys
import json

STATUS_ASSIGN_RE = re.compile(r"(?<![A-Za-z0-9_])status\s*=\s*(?:\$\(|`)")

_SEP = r"(?:\A|(?<=[;\n(])|(?<=&&)|(?<=\|\|)|(?<=\|))"
UNALIASED_RM_MV_CP_RE = re.compile(_SEP + r"[ \t]*(rm|mv|cp)\b")
UNALIASED_HTOP_RE = re.compile(_SEP + r"[ \t]*htop\b")

BASH_DASH_N_RE = re.compile(r"\bbash\s+(?:[A-Za-z-]+\s+)*-n\b")


def find_violations(command):
    violations = []

    if STATUS_ASSIGN_RE.search(command):
        violations.append((
            "zsh-status-readonly",
            "a variable literally named `status` is being assigned from "
            "command substitution",
            "zsh reserves `status` as a read-only alias for $? - this "
            "assignment fails immediately (\"read-only variable: status\") "
            "and silently kills the surrounding loop/script. Rename the "
            "variable (e.g. `job_status`).",
        ))

    for m in UNALIASED_RM_MV_CP_RE.finditer(command):
        cmd = m.group(1)
        violations.append((
            "unaliased-interactive-alias",
            f"bare `{cmd}` used without a `command ` prefix",
            f"if `{cmd}` is aliased to its -i (interactive-confirm) form in "
            f"this environment, a plain `{cmd}` run non-interactively can "
            f"hang waiting for a y/n that never arrives. Use `command {cmd}` "
            "instead.",
        ))

    if UNALIASED_HTOP_RE.search(command):
        violations.append((
            "unaliased-htop-sudo",
            "bare `htop` used without a `command ` prefix",
            "if `htop` is aliased to `sudo /usr/bin/htop` in this "
            "environment, this triggers an implicit privilege escalation "
            "(a hanging sudo prompt non-interactively, or silent root "
            "execution). Use `command htop` if root isn't actually needed.",
        ))

    if BASH_DASH_N_RE.search(command):
        violations.append((
            "bash-n-not-shellcheck",
            "`bash -n` used to validate a shell script",
            "`bash -n` only checks parse syntax and misses real bugs "
            "(unquoted expansions, misused builtins, unreachable code). Run "
            "`shellcheck <script>` instead.",
        ))

    return violations


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, TypeError):
        sys.exit(0)  # fail open - never block on a hook-input parsing issue

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        sys.exit(0)

    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        sys.exit(0)

    try:
        violations = find_violations(command)
    except Exception:
        sys.exit(0)  # fail open - a bug in the hook must never block real work

    if not violations:
        sys.exit(0)

    lines = [
        "BLOCKED: documented shell scripting gotcha(s) detected in this Bash "
        "command.",
        "",
    ]
    for rule, what, fix in violations:
        lines.append(f"- [{rule}] {what}")
        lines.append(f"  Fix: {fix}")
    lines.append("")
    lines.append("Fix the command and retry.")

    print("\n".join(lines), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
