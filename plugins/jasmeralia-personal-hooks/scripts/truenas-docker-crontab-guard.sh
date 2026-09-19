#!/usr/bin/env bash
# PreToolUse guard: on TrueNAS-directed commands (an ssh one-liner to truenas, or a
# session running natively on the TrueNAS host), deny raw `docker run/restart/start`
# (use the truenas-app wrapper) and raw `crontab` edits (use midclt call
# cronjob.*), per the TrueNAS section of ~/.claude/CLAUDE.md.
#
# Scope: home environment only (typhoon/TrueNAS) -- rinling and gelfling have no
# access to TrueNAS and this never fires for them in practice, but the guard is
# host-detection based rather than repo-scoped so it travels correctly regardless
# of which checkout it runs from.
#
# Both branches require the TrueNAS-target match AND the docker/crontab pattern,
# so a command that merely mentions "truenas" in passing (e.g. grepping /etc/hosts)
# does not false-trigger.
#
# Matcher: Bash
set -uo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"

is_truenas_target=0
if printf '%s' "$command" | grep -Eqi 'truenas\.windsofstorm\.net|morgan@truenas\b'; then
  is_truenas_target=1
fi
if [ "$(hostname 2>/dev/null)" = "truenas" ]; then
  is_truenas_target=1
fi

if [ "$is_truenas_target" = "1" ]; then
  if printf '%s' "$command" | grep -Eq 'docker[[:space:]]+(run|restart|start)\b'; then
    jq -n --arg reason "Raw 'docker run/restart/start' targeting TrueNAS. Use the truenas-app wrapper instead (truenas-app classify/list/update-image/pull-latest/start/restart) -- see ~/.claude/CLAUDE.md TrueNAS section." \
      '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":$reason}}'
    exit 0
  fi
  if printf '%s' "$command" | grep -Eq '\bcrontab\b'; then
    jq -n --arg reason "Raw 'crontab' targeting TrueNAS. TrueNAS manages scheduled jobs in its middleware config database, not raw user crontabs -- use 'midclt call cronjob.query/create/update/delete' instead. A raw crontab entry is lost on the next OS-upgrade boot-environment swap." \
      '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":$reason}}'
    exit 0
  fi
fi
exit 0
