# weekly-worklog

Two [Claude Code skills](https://docs.claude.com/en/docs/claude-code) that compile your worklog entries by
cross-referencing your local Claude Code session history, your team chat, and your Chrome browsing history, so
you're not reconstructing "what did I actually do" from memory every time a report is due.

| Skill | Cadence | Output |
|---|---|---|
| [`weekly-worklog`](weekly-worklog/) | weekly | last week's completed work (summary) + this week's plan (task / deliverable / hours table, sums to a full work week) |
| [`daily-worklog`](daily-worklog/) | daily | today's completed work only (task / hours table, sums to a full work day) — retrospective, no forward-looking plan |

They share the same three data sources (including a bundled `read-chrome-history.py` script — no extra MCP setup
needed for that one, just Python) and the same setup placeholders — read `weekly-worklog/SKILL.md` first even if
you only want the daily one, since `daily-worklog/SKILL.md` assumes you've seen it.

## Why

Status reports are annoying to write from memory. These skills reconstruct "what did I actually do" from your
local Claude Code session logs (`~/.claude/projects/*.jsonl`), your Chrome browsing history (cloud console
clicks, doc edits, internal tools — things that never touch Claude Code or chat at all), and optionally your team
chat for anything decided outside of a coding session — then produce a task table with hours that add up to a
real work period, applying a few judgment calls about time-boxing that are easy to get wrong (e.g. not logging 5
days for a task that's just waiting on someone else's approval).

## Quickstart

**1. Get the skill onto your machine**

```sh
git clone https://github.com/eunhyekim-bespinglobal/weekly-worklog-skill.git
cp -r weekly-worklog-skill/weekly-worklog ~/.claude/skills/
cp -r weekly-worklog-skill/daily-worklog ~/.claude/skills/    # optional, if you also want the daily version
```

(On Windows, that's `~/.claude/skills` → `C:\Users\<you>\.claude\skills\`.) No build step, no dependencies to
install — Claude Code auto-discovers anything under `~/.claude/skills/*/SKILL.md`. Copy either folder
independently if you only want one of the two.

**2. Fill in your config**

These skills ship generic on purpose — they don't know your company's worklog tool, your chat platform, or which
projects matter to you. Open `weekly-worklog/SKILL.md` and replace the placeholders under **Setup** at the top
(if you're also installing `daily-worklog`, it reuses the same values — see its own SKILL.md for the one
daily-specific setting, your hours-per-day target):

| Placeholder | What to put there |
|---|---|
| `<YOUR_WORKLOG_URL>` | Where your team's weekly log actually lives |
| `<YOUR_WORKLOG_FORMAT>` | The exact columns/format your tool expects (default assumes task / deliverable / hours, 40h/week) |
| `<YOUR_CHAT_TOOL>` | Slack, Google Chat, Teams, etc. — whatever MCP tool gives Claude access to it |
| `<YOUR_PRIMARY_WORK_CONTEXT>` | A short description of your main project/team, so Claude can tell relevant channels/repos from noise |

**Don't commit your filled-in config if it contains internal URLs, project/client names, or anything else
company-confidential.** If you version-control your own `~/.claude/skills`, keep your personal values in a
separate `config.md` you `.gitignore`, per the note at the bottom of `SKILL.md`.

**Example: what a filled-in Setup looks like**

Placeholders can feel abstract until you see one filled in. Here's a fictional (not a real company) example —
say you're on the platform team at "Acme," tracking work in an internal tool, chatting in Slack:

| Placeholder | Example filled-in value |
|---|---|
| `<YOUR_WORKLOG_URL>` | `https://worklog.acme-internal.com/weekly?team=platform` |
| `<YOUR_WORKLOG_FORMAT>` | 3 columns — Task / Output / Hours — summing to 40h/week |
| `<YOUR_CHAT_TOOL>` | Slack, via the `slack` MCP connector |
| `<YOUR_PRIMARY_WORK_CONTEXT>` | "Platform team; repos are `payments-service` and `checkout-web`; primary Slack channel is `#platform-eng`" |
| Name/handle to search chat for | `Jamie Lee` / `@jamie` |

With those in place, the opening paragraph of `SKILL.md` ends up reading something like:

> Every Monday I log a weekly entry at `https://worklog.acme-internal.com/weekly?team=platform`. This skill
> reconstructs what I did last week and what I need to do this week from my local Claude Code session history
> and Slack.

You don't have to rewrite prose sentence-by-sentence — swapping each bracketed placeholder for your own value
throughout the file is enough. The goal is that by the time you're done, the skill reads like it was written for
your job specifically, not like a template with blanks left in it.

**3. (Optional) connect a chat tool**

Step 2 of the skill cross-references your team chat, but it needs an MCP tool that can actually read it —
a browser MCP with an already-logged-in session (e.g. `claude-in-chrome`) for browser-based chat, or a
dedicated Slack/Teams MCP connector. If you don't have one set up, don't worry about it: skip this, and the
skill still works fine off your local session logs and browser history alone — you'll just be missing anything
that only happened in chat (approvals, other people's asks of you, meeting outcomes).

The browser-history step (Step 2.5 in each `SKILL.md`) needs no separate setup beyond Python 3 with its stdlib
`sqlite3` module (already true for any normal Python install) — the bundled `read-chrome-history.py` reads
Chrome's local history file directly, no MCP or login required.

**4. Run it**

Just ask, in plain language, in Claude Code:

> compile my worklog for this week

or for the daily version:

> what did I get done today?

Each skill's description is written to trigger on phrasing like this, so you don't need to remember an exact
command — see the relevant `SKILL.md`'s frontmatter for the full trigger conditions if it doesn't fire for you.

## First run — what to expect

Nothing runs silently. On a typical first run:

1. Claude tells you it's scanning `~/.claude/projects` for session files since your chosen start date, and hands
   that off to a background agent so it isn't blocking.
2. If you have a chat MCP connected, Claude opens it in parallel and tells you which channels/spaces it's
   checking (and which it's skipping as irrelevant or personal).
3. Claude runs `read-chrome-history.py` for the same date range and reads back the (auth-token-stripped) result —
   again telling you what it's doing, not doing it silently.
4. You get a **"last week" summary** grouped by project — plain bullet points, not a table, since this part is
   informational.
5. You get a **"this week" table** in the exact column format from your config, with hours summing to a full
   work week, e.g.:

   | 업무내용 | 관련산출물 | 시간 |
   |---|---|---|
   | Follow up on the pending access request (5-business-day lead time per IT) | Approval confirmation | 4h |
   | ... | ... | ... |

6. Claude asks if you want anything adjusted before you paste it into your actual worklog tool — the first draft
   is a starting point, not gospel. Tell it what's wrong (wrong scope, missing task, hours off) and it'll redo
   that table on the spot.

If it comes back with barely anything for "last week," that usually means there just wasn't much local Claude
Code session activity in the date range — check that your date range is right, or that you were coding somewhere
other than through Claude Code that week (this skill only sees what's in `~/.claude/projects`).

## What these skills do *not* do

- They do not automatically log into any chat tool or handle credentials.
- Neither ships wired to an automatic trigger — invoke them yourself (e.g. every Monday / every evening), since
  they depend on local filesystem access and (for the chat step) an actively logged-in browser session that a
  cloud scheduler can't reach. Each `SKILL.md` has an "Optional: automating this on a schedule" section covering
  the pitfalls if you want to wire up local OS-level scheduling anyway (Task Scheduler, cron, launchd).
- They will not surface or summarize personal/casual chat content about you or your coworkers, even if it's in a
  channel otherwise being scanned for work context.
- `read-chrome-history.py` strips OAuth/SSO/session-token-looking URLs mechanically, at the script level, before
  that text ever reaches the model — not as a "please don't repeat this" instruction the model could still get
  wrong. Personal (non-work) browsing is a separate, judgment-based filter applied when the model compiles the
  report, same as personal chat.

## License

MIT — see [LICENSE](LICENSE).
