# weekly-worklog

A [Claude Code skill](https://docs.claude.com/en/docs/claude-code) that compiles your weekly worklog entry —
last week's completed work plus this week's plan, time-boxed to a full work week — by cross-referencing your
local Claude Code session history with your team chat.

## Why

Weekly status reports are annoying to write from memory. This skill reconstructs "what did I actually do last
week" from your local Claude Code session logs (`~/.claude/projects/*.jsonl`), optionally cross-references your
team chat for anything decided outside of a coding session, and produces a "this week" task table with hours
that add up to a real work week — applying a few judgment calls about time-boxing that are easy to get wrong
(e.g. not logging 5 days for a task that's just waiting on someone else's approval).

## Install

Copy the `weekly-worklog/` folder into your `~/.claude/skills/` directory:

```sh
cp -r weekly-worklog ~/.claude/skills/
```

Then invoke it by asking Claude Code something like "compile my worklog for this week" — see the skill's
description in `weekly-worklog/SKILL.md` for the exact trigger phrases.

## Configure

This skill ships generic on purpose — it doesn't know your company's worklog tool, your chat platform, or which
projects matter to you. Open `weekly-worklog/SKILL.md` and fill in the placeholders under **Setup** at the top:

| Placeholder | What to put there |
|---|---|
| `<YOUR_WORKLOG_URL>` | Where your team's weekly log actually lives |
| `<YOUR_WORKLOG_FORMAT>` | The exact columns/format your tool expects (default assumes task / deliverable / hours, 40h/week) |
| `<YOUR_CHAT_TOOL>` | Slack, Google Chat, Teams, etc. — whatever MCP tool gives Claude access to it |
| `<YOUR_PRIMARY_WORK_CONTEXT>` | A short description of your main project/team, so Claude can tell relevant channels/repos from noise |

The chat cross-reference (Step 2) is optional — the skill still works with just your local session logs if you
don't have a chat MCP tool connected.

**Don't commit your filled-in config if it contains internal URLs, project/client names, or anything else
company-confidential.** If you version-control your own `~/.claude/skills`, keep your personal values in a
separate `config.md` you `.gitignore`, per the note at the bottom of `SKILL.md`.

## What it does *not* do

- It does not automatically log into any chat tool or handle credentials.
- It is not scheduled to run automatically — invoke it yourself (e.g. every Monday), since it depends on local
  filesystem access and (for the chat step) an actively logged-in browser session.
- It will not surface or summarize personal/casual chat content about you or your coworkers, even if it's in a
  channel it's otherwise scanning for work context.

## License

MIT — see [LICENSE](LICENSE).
