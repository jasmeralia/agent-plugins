# jasmeralia-nonbinary-hooks

A pronoun-slip guard for nonbinary people, built from real slips affecting
Jasmeralia, Morgan, and Nathan - three nonbinary identities that use
they/them and have each had a gendered pronoun slip into a memory note or
hook docstring at least once. Install this if you (or the people you write
about in your own memory/hook files) are also nonbinary and want the same
mechanical backstop.

| Script | Event | Matcher | What it does |
|---|---|---|---|
| `check-pronoun-slip.py` | PreToolUse | `Write\|Edit` | Warns when a gendered pronoun (he/him/his/himself/she/her/hers/herself) appears in a write to a memory or hook-script file. |

The regex is identity-agnostic - it flags any gendered pronoun in the scoped
paths (`/memory/`, `/.claude/hooks/`), not a specific name, and leaves it to
you to judge whether a hit is a real slip or a quoted third party's own
pronouns.

## Cross-ecosystem support

- **Claude Code**: `.claude-plugin/plugin.json` + `hooks/hooks.json`.
- **Codex**: root `plugin.json` (Agent Plugins standard) reuses the same
  `hooks/hooks.json`.
- **Cursor**: `.cursor-plugin/plugin.json` + `hooks/cursor-hooks.json`
  (`preToolUse` / `Write`, which also covers `Edit` per Cursor's tool-name
  mapping).
