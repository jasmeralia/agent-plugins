#!/usr/bin/env bash
# PostToolUse (Bash) hook: two checks after every Bash command.
#
# 1. If the command was a `git pull`, remind the agent to re-read any
#    AGENTS.md/CLAUDE.md in the current directory, since the pull may have
#    brought in revised guidance that supersedes what is already in context.
# 2. Compare the global ~/.claude/CLAUDE.md's hash against the baseline this
#    session recorded at SessionStart (see claude-md-baseline.sh). If it
#    changed on disk mid-session, inject the current content directly as
#    authoritative context, since the model's in-context copy is now stale.
set -uo pipefail

input="$(cat)"
c="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
sid="$(printf '%s' "$input" | jq -r '.session_id // "unknown"')"

is_git_pull=0
if printf '%s' "$c" | grep -Eq '(^|[;&|`(]|[[:space:]])git([[:space:]]+-[A-Za-z-]+([[:space:]]+[^[:space:]]+)?)*[[:space:]]+pull([[:space:]]|$)'; then
  is_git_pull=1
fi

ctx=""
if [ "$is_git_pull" = "1" ]; then
  ctx="A git pull just ran. If this directory has an AGENTS.md or CLAUDE.md, re-read it now via the Read tool before continuing on anything it covers, since the pull may have brought in new or revised guidance that supersedes what is already in context."
fi

global_md="$HOME/.claude/CLAUDE.md"
state_dir="$HOME/.claude/hook-state"
mkdir -p "$state_dir" 2>/dev/null
state_file="$state_dir/claude-md-hash-$sid"

if [ -f "$global_md" ]; then
  cur_hash=$( (sha256sum "$global_md" 2>/dev/null || shasum -a 256 "$global_md" 2>/dev/null) | cut -d' ' -f1)
  old_hash=""
  [ -f "$state_file" ] && old_hash="$(cat "$state_file" 2>/dev/null)"
  if [ -n "$old_hash" ] && [ "$cur_hash" != "$old_hash" ]; then
    content="$(cat "$global_md")"
    header="\$HOME/.claude/CLAUDE.md (global user-level instructions) changed on disk since this session started -- the content below is CURRENT and supersedes anything from that file already in context. Detected deterministically via hash comparison, not inferred, so treat as authoritative regardless of whether the triggering command seems repo-related:"
    note="$(printf '%s\n\n---\n%s\n---' "$header" "$content")"
    if [ -n "$ctx" ]; then ctx="$(printf '%s\n\n%s' "$ctx" "$note")"; else ctx="$note"; fi
  fi
  printf '%s' "$cur_hash" > "$state_file" 2>/dev/null
fi

if [ -n "$ctx" ]; then
  jq -n --arg ctx "$ctx" '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":$ctx}}'
fi
