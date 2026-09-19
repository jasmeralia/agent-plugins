# jasmeralia-personal-hooks

Morgan/Jasmeralia's personal infrastructure and workflow-policy guard hooks.
Not employer-specific, but tied to Morgan's own home infra (TrueNAS, EC2
instances) and personal accounts (Odoo) - install this if you're Morgan or
running the same infra, not as a general-purpose team plugin.

| Script | Event | Matcher | What it does |
|---|---|---|---|
| `memory-vs-agents-guard.sh` | PreToolUse | `Write\|Edit` | Asks for confirmation before writing to Claude's private auto-memory instead of AGENTS.md/CLAUDE.md. |
| `odoo-task-close-guard.sh` | PreToolUse | `mcp__odoo__update_record` | Reminds to set `state: "1_done"` alongside `stage_id` when closing a `project.task`. |
| `validate_odoo_html.py` | PreToolUse | `mcp__odoo__post_message\|update_record\|create_record` | Rejects Odoo chatter/description HTML that Odoo would render as escaped text. |
| `ec2-destructive-guard.sh` | PreToolUse | `Bash` | Denies `aws ec2 terminate-instances`; asks for confirmation on `stop-instances`/`reboot-instances`. |
| `truenas-docker-crontab-guard.sh` | PreToolUse | `Bash` | On TrueNAS-directed commands, denies raw `docker run/restart/start` and raw `crontab` edits. |
| `claude-md-baseline.sh` | SessionStart | - | Records a hash of `~/.claude/CLAUDE.md` as this session's baseline. |
| `claude-md-diff-check.sh` | PostToolUse | `Bash` | Flags `git pull`, and injects the current `~/.claude/CLAUDE.md` content if it changed on disk mid-session. |
| `webfetch-auth-wall-reminder.sh` | PostToolUse | `WebFetch` | Detects an auth-wall response, reminds to re-scan the full MCP tool list before concluding "no access". |

## Cross-ecosystem support

- **Claude Code**: `.claude-plugin/plugin.json` + `hooks/hooks.json`.
- **Codex**: root `plugin.json` (Agent Plugins standard) reuses the same
  `hooks/hooks.json`.
- **Cursor**: `.cursor-plugin/plugin.json` + a hand-translated
  `hooks/cursor-hooks.json`, covering the five hooks that have a clean
  Cursor equivalent.

Three hooks are **Claude Code-only** and intentionally omitted from
`cursor-hooks.json`:
- `claude-md-baseline.sh` / `claude-md-diff-check.sh` - hardcode
  `~/.claude/CLAUDE.md` and `~/.claude/hook-state`, which are Claude Code
  concepts specifically (Codex has its own separate, existing mechanism for
  tracking `~/.codex/AGENTS.md`, out of scope for this plugin).
- `webfetch-auth-wall-reminder.sh` - no confirmed Cursor tool-matcher name
  for WebFetch in Cursor's native `preToolUse`/`postToolUse` vocabulary
  (`Shell`/`Read`/`Write`/`Task`/`MCP:<tool>`), so it's omitted rather than
  guessed at.

**Odoo MCP tool-name matchers in `cursor-hooks.json` are a best guess**
(`MCP:odoo_update_record` etc.) using Cursor's documented `MCP:<tool_name>`
convention - confirm against Cursor's actual MCP tool naming the first time
this plugin is installed there, and correct if it doesn't match.
