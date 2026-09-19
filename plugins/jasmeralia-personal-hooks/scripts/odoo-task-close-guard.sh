#!/usr/bin/env bash
# PreToolUse guard: ask for confirmation when a project.task update sets stage_id
# without also setting state. Closing a task requires BOTH fields -- stage_id alone
# leaves state as "01_in_progress", so the task still reads as active despite being
# in the done column.
#
# This is `ask` rather than `deny` because plenty of legitimate stage moves are not
# a close-out (e.g. moving between two in-progress stages), so a hard block would
# false-positive too often.
#
# Matcher: mcp__odoo__update_record
set -uo pipefail

input="$(cat)"
model="$(printf '%s' "$input" | jq -r '.tool_input.model // empty')"

if [ "$model" = "project.task" ]; then
  has_stage="$(printf '%s' "$input" | jq -r '(.tool_input.values // {}) | has("stage_id")')"
  has_state="$(printf '%s' "$input" | jq -r '(.tool_input.values // {}) | has("state")')"
  if [ "$has_stage" = "true" ] && [ "$has_state" != "true" ]; then
    jq -n --arg reason 'Updating project.task stage_id without state in the same call. If this is closing the task, Odoo also needs state: "1_done" -- setting stage_id alone leaves it showing as in-progress. If this is just a non-terminal stage move, it is fine to proceed as-is.' \
      '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":$reason}}'
  fi
fi
exit 0
