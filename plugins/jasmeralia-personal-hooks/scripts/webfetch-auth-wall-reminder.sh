#!/usr/bin/env bash
# PostToolUse (WebFetch) hook: detect a response that looks like it hit an
# auth/login wall, and remind the agent to re-scan the full enumerated tool
# list for a matching mcp__<server>__* tool before concluding a capability
# isn't available. MCP tools are namespaced and easy to miss on a fast scan
# next to the small set of always-present built-ins.
set -uo pipefail

input="$(cat)"
matches="$(printf '%s' "$input" | jq -r '.tool_response | .. | strings' 2>/dev/null | grep -iE 'log[ -]?in|sign[ -]?in|authenticate|session (has )?expired|unauthorized|access denied|please (log|sign) in' | head -1)"

if [ -n "$matches" ]; then
  ctx="This WebFetch result looks like it hit an authentication/login wall rather than real page content. Before concluding that a capability or external service is not available in this session, re-scan the FULL enumerated tool list for a matching mcp__<server>__* tool -- MCP tools are namespaced (mcp__servername__toolname) and are easy to miss on a fast scan. Do not conclude \"no access\" based on a WebFetch failure alone."
  jq -n --arg ctx "$ctx" '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":$ctx}}'
fi
