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

## Quickstart

**1. Get the skill onto your machine**

```sh
git clone https://github.com/eunhyekim-bespinglobal/weekly-worklog-skill.git
cp -r weekly-worklog-skill/weekly-worklog ~/.claude/skills/
```

(On Windows, that's `~/.claude/skills` → `C:\Users\<you>\.claude\skills\`.) No build step, no dependencies to
install — Claude Code auto-discovers anything under `~/.claude/skills/*/SKILL.md`.

**2. Fill in your config**

This skill ships generic on purpose — it doesn't know your company's worklog tool, your chat platform, or which
projects matter to you. Open `weekly-worklog/SKILL.md` and replace the placeholders under **Setup** at the top:

| Placeholder | What to put there |
|---|---|
| `<YOUR_WORKLOG_URL>` | Where your team's weekly log actually lives |
| `<YOUR_WORKLOG_FORMAT>` | The exact columns/format your tool expects (default assumes task / deliverable / hours, 40h/week) |
| `<YOUR_CHAT_TOOL>` | Slack, Google Chat, Teams, etc. — whatever MCP tool gives Claude access to it |
| `<YOUR_PRIMARY_WORK_CONTEXT>` | A short description of your main project/team, so Claude can tell relevant channels/repos from noise |

**Don't commit your filled-in config if it contains internal URLs, project/client names, or anything else
company-confidential.** If you version-control your own `~/.claude/skills`, keep your personal values in a
separate `config.md` you `.gitignore`, per the note at the bottom of `SKILL.md`.

**3. (Optional) connect a chat tool**

Step 2 of the skill cross-references your team chat, but it needs an MCP tool that can actually read it —
a browser MCP with an already-logged-in session (e.g. `claude-in-chrome`) for browser-based chat, or a
dedicated Slack/Teams MCP connector. If you don't have one set up, don't worry about it: skip this, and the
skill still works fine off your local session logs alone — you'll just be missing anything that only happened
in chat (approvals, other people's asks of you, meeting outcomes).

**4. Run it**

Just ask, in plain language, in Claude Code:

> compile my worklog for this week

or in Korean: `이번주 워크로그 정리해줘`. The skill's description is written to trigger on phrasing like this, so
you don't need to remember an exact command — see `weekly-worklog/SKILL.md`'s frontmatter for the full trigger
conditions if it doesn't fire for you.

## First run — what to expect

Nothing runs silently. On a typical first run:

1. Claude tells you it's scanning `~/.claude/projects` for session files since your chosen start date, and hands
   that off to a background agent so it isn't blocking.
2. If you have a chat MCP connected, Claude opens it in parallel and tells you which channels/spaces it's
   checking (and which it's skipping as irrelevant or personal).
3. You get a **"last week" summary** grouped by project — plain bullet points, not a table, since this part is
   informational.
4. You get a **"this week" table** in the exact column format from your config, with hours summing to a full
   work week, e.g.:

   | 업무내용 | 관련산출물 | 시간 |
   |---|---|---|
   | Follow up on the pending access request (5-business-day lead time per IT) | Approval confirmation | 4h |
   | ... | ... | ... |

5. Claude asks if you want anything adjusted before you paste it into your actual worklog tool — the first draft
   is a starting point, not gospel. Tell it what's wrong (wrong scope, missing task, hours off) and it'll redo
   that table on the spot.

If it comes back with barely anything for "last week," that usually means there just wasn't much local Claude
Code session activity in the date range — check that your date range is right, or that you were coding somewhere
other than through Claude Code that week (this skill only sees what's in `~/.claude/projects`).

## What it does *not* do

- It does not automatically log into any chat tool or handle credentials.
- It is not scheduled to run automatically — invoke it yourself (e.g. every Monday), since it depends on local
  filesystem access and (for the chat step) an actively logged-in browser session.
- It will not surface or summarize personal/casual chat content about you or your coworkers, even if it's in a
  channel it's otherwise scanning for work context.

## License

MIT — see [LICENSE](LICENSE).
