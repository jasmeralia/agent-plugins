#!/usr/bin/env bash
# PreToolUse guard: enforce this repo's EC2 safety policy on raw AWS CLI calls.
# - `aws ec2 terminate-instances` is always denied -- termination must be done
#   manually by Morgan (AWS console or a direct CLI invocation), never from an agent.
# - `aws ec2 stop-instances` / `reboot-instances` requires explicit confirmation
#   (ask), which forces the interactive prompt for gelfling even under an
#   auto-accept session setting.
# `scripts/rinling-power.sh` is unaffected: its internal `aws ec2` invocation runs
# inside the script process, never appearing as the literal Bash tool_input.command
# Claude issues, so there's no collision with the rinling "no confirmation needed"
# policy.
#
# Matcher: Bash
set -uo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"

if printf '%s' "$command" | grep -Eq 'aws[[:space:]]+ec2[[:space:]]+terminate-instances'; then
  jq -n --arg reason "Never terminate an EC2 instance from an agent (rincity-infra CLAUDE.md EC2 Instance Management). Termination is destructive and unrecoverable -- it requires Morgan to execute it manually via the AWS console or a direct CLI invocation." \
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":$reason}}'
  exit 0
fi

if printf '%s' "$command" | grep -Eq 'aws[[:space:]]+ec2[[:space:]]+(stop-instances|reboot-instances)'; then
  jq -n --arg reason "Raw aws ec2 stop-instances/reboot-instances detected. Per project policy: rinling should go through scripts/rinling-power.sh instead of raw AWS CLI, and gelfling power-state changes always require explicit confirmation regardless of session auto-accept settings. Confirm this is intended before proceeding." \
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":$reason}}'
fi
exit 0
