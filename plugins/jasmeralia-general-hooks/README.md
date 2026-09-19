# jasmeralia-general-hooks

Universal shell/git/tooling hygiene hooks. No personal infrastructure or
employer specifics - safe to install regardless of who or what team you are.

| Script | Event | Matcher | What it does |
|---|---|---|---|
| `check-bash-gotchas.py` | PreToolUse | `Bash` | Blocks a documented set of zsh/shell footguns (bare `status=`, unaliased `rm`/`mv`/`cp`/`htop`, `bash -n` instead of `shellcheck`). |
| `remind_serena.py` | PreToolUse | `Grep\|Glob` | Advisory reminder to prefer Serena's semantic search tools over raw Grep/Glob for code. |
| `check-typography.py` | PreToolUse | `Write\|Edit` | Blocks smart quotes/en-dash/em-dash/NBSP in files inside a git repo. |
| `check-secret-decrypt.py` | PreToolUse | `Bash` | Blocks AWS SSM/Secrets Manager decrypt commands - run those yourself instead. |
| `check-pr-description-stale.py` | PostToolUse | `Bash` (`git push`) | Reminds you to check the open PR's description after a push. |
| `codex-isolation-guard.sh` | PreToolUse | `Agent` | Denies a Codex subagent call combined with `isolation: "worktree"` (known sandbox-write race). |

## Cross-ecosystem support

- **Claude Code**: `.claude-plugin/plugin.json` + `hooks/hooks.json`.
- **Codex**: root `plugin.json` (Agent Plugins standard) reuses the same
  `hooks/hooks.json` - Codex uses the same PascalCase event names and sets
  `CLAUDE_PLUGIN_ROOT` for compatibility.
- **Cursor**: `.cursor-plugin/plugin.json` + a hand-translated
  `hooks/cursor-hooks.json` (camelCase events, `Shell`/`Write` tool names,
  `${CURSOR_PLUGIN_ROOT}` paths).

Two hooks have **no Cursor translation** and are intentionally omitted from
`cursor-hooks.json`:
- `remind_serena.py` - Cursor's `preToolUse` matcher vocabulary (`Shell`,
  `Read`, `Write`, `Task`, `MCP:<tool>`) has no distinct `Grep`/`Glob` tool
  kind to match against.
- `codex-isolation-guard.sh` - guards a Claude Code `Agent`-tool parameter
  combination specific to the Claude Code + Codex plugin pairing, which has
  no equivalent in Cursor's own subagent model.
