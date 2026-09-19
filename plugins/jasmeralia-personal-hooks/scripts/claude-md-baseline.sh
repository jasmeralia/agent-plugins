#!/usr/bin/env bash
# SessionStart hook: record a hash of the global CLAUDE.md as this session's
# baseline, so claude-md-diff-check.sh can later detect if it changed on disk
# mid-session (e.g. edited in another session, or updated by a git pull of a
# dotfiles repo) and surface the current content as authoritative.
set -uo pipefail

input="$(cat)"
sid="$(printf '%s' "$input" | jq -r '.session_id // "unknown"')"
state_dir="$HOME/.claude/hook-state"
mkdir -p "$state_dir" 2>/dev/null
global_md="$HOME/.claude/CLAUDE.md"

if [ -f "$global_md" ]; then
  cur_hash=$( (sha256sum "$global_md" 2>/dev/null || shasum -a 256 "$global_md" 2>/dev/null) | cut -d' ' -f1)
  printf '%s' "$cur_hash" > "$state_dir/claude-md-hash-$sid" 2>/dev/null
fi
