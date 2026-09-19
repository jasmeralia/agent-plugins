# agent-plugins

Morgan/Jasmeralia's Claude Code / Codex / Cursor hook conventions, packaged
as installable plugins.

Pattern: `hooks/hooks.json` declares the automation, `scripts/` holds
whatever the hooks shell out to, and a marketplace manifest declares the
plugin(s) this repo distributes.

## Plugins

| Plugin | Audience | Description |
|---|---|---|
| [`jasmeralia-general-hooks`](plugins/jasmeralia-general-hooks) | Anyone | Universal shell/git/tooling hygiene hooks - no personal or employer specifics. |
| [`jasmeralia-personal-hooks`](plugins/jasmeralia-personal-hooks) | Morgan/Jasmeralia | Personal-infra and workflow-policy guard hooks (TrueNAS, EC2, Odoo, memory policy, CLAUDE.md tracking). |
| [`jasmeralia-work-hooks`](plugins/jasmeralia-work-hooks) | Anyone using similar Jira/Confluence/PagerDuty/Kibana tooling | Employer-tool workflow guard hooks, genericized of any one person's name or employer specifics. |
| [`jasmeralia-nonbinary-hooks`](plugins/jasmeralia-nonbinary-hooks) | Nonbinary people/teams | Pronoun-slip guard for nonbinary people and nonbinary plugin users. |

Each plugin's own README documents its hooks and any cross-ecosystem gaps.

## Cross-ecosystem support

This repo is a marketplace for three agent ecosystems, each with its own
manifest and marketplace file:

| | Claude Code | Codex | Cursor |
|---|---|---|---|
| Marketplace | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` | `.cursor-plugin/marketplace.json` |
| Per-plugin manifest | `plugins/<name>/.claude-plugin/plugin.json` | `plugins/<name>/plugin.json` | `plugins/<name>/.cursor-plugin/plugin.json` |
| Hooks file | `plugins/<name>/hooks/hooks.json` | same file (Codex shares Claude's PascalCase event names and matcher vocabulary, and sets `CLAUDE_PLUGIN_ROOT` for compatibility) | `plugins/<name>/hooks/cursor-hooks.json` (hand-translated: camelCase events, `Shell`/`Write` tool names, `${CURSOR_PLUGIN_ROOT}` paths) |

Every hook's actual logic lives once, in each plugin's `scripts/` directory.
Only the hook *wiring* is duplicated per ecosystem where the schemas differ.
Some hooks have no clean Cursor translation (no matching tool-matcher
vocabulary) and are intentionally omitted from `cursor-hooks.json` rather
than guessed at - see each plugin's README for specifics.

## Install

**Claude Code:**
```
/plugin marketplace add <this-repo-url-or-path>
/plugin install jasmeralia-general-hooks@agent-plugins
```

**Codex:** add this repo as a local marketplace catalog per Codex's plugin
docs (`.agents/plugins/marketplace.json`), then install the plugin(s) you
want.

**Cursor:** add this repo as a marketplace source per Cursor's plugin docs
(`.cursor-plugin/marketplace.json`), then install the plugin(s) you want.
Confirm "Include Third-Party Plugins, Skills, and Other Configs" doesn't
need to be separately enabled for marketplace-installed plugins (it's a
different code path from Cursor's Claude-`settings.json` import shim).

## Linting

```
make lint      # shellcheck + ruff + JSON syntax + yamllint
make validate  # claude plugin validate for every plugin
```

`make lint` bootstraps its own `.venv/` with pinned `ruff`/`yamllint`
versions from `requirements-dev.txt` (requires `python3`, `shellcheck`, and
`jq` on PATH already) - no manual setup needed, and results are the same
locally and in CI regardless of what's globally installed. CI runs
`make lint` on every PR and on push to `master` (see
`.github/workflows/lint.yml`).

## License

MIT - see [LICENSE](LICENSE).
