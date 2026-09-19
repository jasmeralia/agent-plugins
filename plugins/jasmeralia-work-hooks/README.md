# jasmeralia-work-hooks

Jira/Confluence/PagerDuty/Kibana workflow guard hooks, genericized from a
specific employer's setup: any mention of a specific person's name or
employer/repo-identifying detail has been stripped from comments and
docstrings. The underlying detection logic is unchanged.

| Script | Event | Matcher | What it does |
|---|---|---|---|
| `validate-atlassian-markdown.py` | PreToolUse | Jira/Confluence create/update/comment tools | Blocks confirmed-real markdown rendering bugs (bare URLs, broken @mentions, bold spans containing links/issue keys, paren-backtick adjacency). |
| `check-jira-priority-default.py` | PreToolUse | `jira_create_issue\|jira_update_issue` | Warns when a sub-task is about to be filed at P2 - reminder to double check urgency. |
| `check-jira-devops-workflow-reassign.py` | PreToolUse | `jira_transition_issue` | Warns before transitioning a DEVOPS-project issue that its assignee may change as an intentional workflow side effect. |
| `check-kibana-index-scope.py` | PreToolUse | Kibana search tool | Blocks unscoped `filebeat-*`/`filebeat-k8s-events-*` index wildcards. |
| `check-pagerduty-note-format.py` | PreToolUse | `add_note_to_incident` | Enforces the `"WI: <url>"` PagerDuty note format. |
| `remind-pd-list-incidents.py` | PreToolUse | `list_incidents` | Advisory: warns about silent filter/scoping gaps in this tool. |
| `remind-pd-historical-incidents.py` | PreToolUse | `get_past_incidents\|get_related_incidents` | Advisory: warns these tools 403 without a specific PagerDuty add-on. |

## Matchers

The Claude/Codex `hooks.json` matches the generic, commonly-published MCP
server names (`mcp-atlassian`, `pagerduty-mcp`, `kibana-mcp`). If you have a
second Atlassian/PagerDuty account behind a differently-named MCP server,
add your own matcher entries locally (or in a project-level
`.claude/settings.json` override) rather than expecting this plugin to guess
your server naming.

## Cross-ecosystem support

- **Claude Code**: `.claude-plugin/plugin.json` + `hooks/hooks.json`.
- **Codex**: root `plugin.json` (Agent Plugins standard) reuses the same
  `hooks/hooks.json`.
- **Cursor**: `.cursor-plugin/plugin.json` + `hooks/cursor-hooks.json`, using
  Cursor's `MCP:<tool_name>` matcher convention with a regex alternation
  where a hook covers multiple tools. **Best-effort**: the exact
  `MCP:<tool_name>` naming (e.g. whether it's `MCP:search` or something more
  qualified for the Kibana tool) is not independently confirmed - verify
  against Cursor's actual MCP tool naming on first install and correct if it
  doesn't match.
