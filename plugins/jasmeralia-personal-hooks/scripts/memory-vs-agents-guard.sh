#!/usr/bin/env bash
# PreToolUse guard: ask for confirmation before writing to Claude Code's private
# auto-memory store (~/.claude/projects/*/memory/). Per Morgan's instruction
# (2026-09-19), memory should be the exception, not the default: Morgan regularly
# uses Claude, Codex, and Cursor against the same repos, and Claude's auto-memory is
# invisible to the other two. Most learnings belong in the project's AGENTS.md (or
# CLAUDE.md) instead, since every agent reads that.
#
# This is `ask` rather than `deny` because memory is sometimes the right place --
# see the three exceptions in the reason text below -- so a hard block would
# false-positive too often.
#
# Matcher: Write|Edit
set -uo pipefail

input="$(cat)"
file_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"

if printf '%s' "$file_path" | grep -Eq "^${HOME}/\.claude/projects/[^/]+/memory/"; then
  jq -n --arg reason 'About to write to Claude'"'"'s private auto-memory. Only do this if (a) the content is specific to you as the acting coding agent and would not help Codex or Cursor, (b) this project has no AGENTS.md/CLAUDE.md to update instead, or (c) Morgan explicitly asked you to remember this rather than document it. Otherwise write it to the project'"'"'s AGENTS.md (or CLAUDE.md) so every agent benefits, not just this memory store.' \
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":$reason}}'
fi
exit 0
