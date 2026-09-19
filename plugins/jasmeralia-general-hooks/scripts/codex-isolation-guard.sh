#!/usr/bin/env bash
# PreToolUse guard: deny Agent calls that combine a codex subagent with
# isolation: "worktree". Codex's sandboxed subprocess (workspace-write) can
# intermittently fail to write inside a freshly-created worktree directory
# ("mkdir: Read-only file system") even though the real filesystem is fully
# writable -- a documented race/stale-mount issue between worktree creation and
# Codex's sandbox view being established. There is no known-good use of this
# combination; always deny rather than ask.
#
# Matcher: Agent
set -uo pipefail

input="$(cat)"
subagent_type="$(printf '%s' "$input" | jq -r '.tool_input.subagent_type // empty')"
isolation="$(printf '%s' "$input" | jq -r '.tool_input.isolation // empty')"

if printf '%s' "$subagent_type" | grep -qi '^codex' && [ "$isolation" = "worktree" ]; then
  jq -n --arg reason 'isolation: "worktree" intermittently breaks Codex sandbox writes (mkdir: Read-only file system) when combined with a codex subagent -- a known, documented gotcha. Drop the isolation parameter and let Codex operate directly on the current working directory instead.' \
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":$reason}}'
fi
exit 0
