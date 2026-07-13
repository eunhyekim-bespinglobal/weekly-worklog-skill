---
name: weekly-worklog
description: "Compile a weekly worklog entry (last week's completed work + this week's plan, time-boxed to a full work week, as a task/deliverable/hours table) by cross-referencing local Claude Code session logs and your team chat. Trigger this whenever the user mentions 'worklog', 'weekly report', asks what they did last week / should do this week, or it's the start of the week and they're preparing a status update. Always use this instead of starting from scratch — it encodes judgment calls about how to scope and time-box tasks that are easy to get wrong (padding blocked tasks, logging hours for work that can't start yet, etc)."
---

# Weekly worklog compiler

Many teams require a weekly status log — what got done, what's planned, broken into tasks with time estimates
that should add up to a full work week. This skill reconstructs that from two sources you don't manually track
in real time: your local Claude Code session history, and your team chat tool. It's meant to be invoked manually
(e.g. every Monday) — it is **not** wired to an automatic schedule, because it depends on this machine's local
filesystem and (if you enable the chat step) an actively logged-in browser session, neither of which a cloud/
scheduled run can guarantee.

## Setup — fill these in before first use

This skill ships generic. Before it's useful to you, edit the placeholders below (either directly in this file,
or better, keep your personal values in a `config.md` alongside this one and reference it — see "Keeping your
config out of git" at the bottom):

- `<YOUR_WORKLOG_URL>` — wherever your team's weekly log lives (an internal tool, a wiki page, a spreadsheet).
- `<YOUR_WORKLOG_FORMAT>` — the exact columns/format your tool expects. This SKILL.md assumes a 3-column
  table (task / deliverable / hours) summing to 40 hours — adjust to match your actual tool and work week length.
- `<YOUR_CHAT_TOOL>` — Slack, Google Chat, Teams, etc. Step 2 below is written for Google Chat via the
  `claude-in-chrome` MCP tool as an example; swap in whatever MCP/tool gives you access to your actual chat.
- `<YOUR_PRIMARY_WORK_CONTEXT>` — a description of your main project/client/team so the skill can tell which
  chat channels and repos are actually relevant to your work vs. noise.
- Your name / handle, so the skill can search chat for messages directed at you.

## Why two sources

Neither source alone is enough. Local Claude Code sessions capture the *technical* work (debugging, code changes,
investigations) across your repos, but miss anything decided or requested over chat (meeting outcomes, approvals,
blockers, other people's asks of you). Chat captures the organizational context but not the technical substance.
Combine both — but treat chat as optional if you don't use `claude-in-chrome` or an equivalent; the skill is still
useful with just the local session logs.

## Step 1 — Local session logs

Determine the date range: from the start of last week (or whatever start date the user gives you) through today.

Find candidate session files:

```
find ~/.claude/projects -name "*.jsonl" -newermt "<range-start> 00:00:00" ! -path "*/subagents/*"
```

Exclude the current session's own transcript file — you already know its content. Group the remaining files by
project: the folder name after `.claude/projects/` indicates the repo (Claude Code encodes the working directory
path into the folder name). Folders that don't map to a specific repo are generic/cross-cutting sessions.

These files can be large and contain huge tool_result blocks (file dumps, command output) that aren't worth
reading. Spawn a background `general-purpose` Agent to do the reading rather than doing it inline — hand it the
exact file list (absolute paths) and tell it to:
- Sample large files rather than reading top-to-bottom (first ~150 lines + last ~150 lines, or grep for
  `"role":"user"` for cheap intent extraction).
- Focus on user text messages and assistant text responses, not tool_use/tool_result payloads.
- Return, per project: a one-line tag of what the project is about, what was completed (concrete — file names,
  bugs fixed, features built, decisions made), and what's still pending/TODO/blocked.
- Keep the report under ~900 words — breadth over depth, since there are usually dozens of files.

Launch this in the background (`run_in_background: true`) so you can work on Step 2 in parallel, and mention to
the user that it's running rather than silently waiting on it.

## Step 2 — Team chat (in parallel with Step 1, optional)

If the user has a chat MCP tool connected (e.g. `claude-in-chrome` for a real logged-in browser, or a dedicated
Slack/Teams MCP), use it to check for work-relevant activity in `<YOUR_CHAT_TOOL>`. If nothing is connected, skip
this step and say so rather than guessing.

For browser-based chat (e.g. Google Chat via `claude-in-chrome`): this needs the user's real, already-logged-in
browser — SSO logins won't work from a sandboxed browser pane. If it lands on a login page, tell the user and
wait; never enter credentials yourself.

Go through the channel/DM list and use judgment about what's actually work-relevant:
- Prioritize channels/spaces matching `<YOUR_PRIMARY_WORK_CONTEXT>`.
- Skip channels that are clearly automated feeds (news/market recap bots, CI notification channels) — no human
  back-and-forth, not part of actual work.
- Skip DMs that read as personal/casual. Do not surface or summarize personal content about the user or their
  coworkers even in passing — this is a hard boundary, not just a deprioritization, since it's private
  information about real people.
- Scroll back from today to the range start (batch scroll+screenshot calls rather than one at a time if your
  tool supports it — much faster), noting: work completed, action items directed at the user (search for their
  name/handle), and blockers.

## Step 3 — Compile

Once your source(s) are in, produce two things:

**Last week's completed work** — grouped by project, concrete bullet points combining both sources. This is
informational, not time-boxed.

**This week's plan** — a table matching `<YOUR_WORKLOG_FORMAT>` (default assumption: task / deliverable / hours).

The hours must sum to a full work week (default: 40). Getting this right requires judgment, not just listing
tasks and dividing evenly:

- **External-approval-blocked tasks** (e.g. an access request with a multi-day lead time) get their own line,
  but the hours reflect only *active* hands-on time that week (submitting the request, following up,
  coordinating) — not the full lead time. Mention the lead time in the task description as context, since it
  affects when the *rest* of the dependent work can start, but don't let it inflate logged hours.
- **Tasks blocked on another team finishing something first** get scoped down to only the preparatory/
  collaboration work that can actually happen this week — not the full downstream task. Don't log hours for
  work that literally cannot start yet.
- **Small recurring admin tasks** (writing the report itself, quick status replies) get realistic small time
  (~1h), not padded to fill space.
- **Exclude tasks that aren't the user's job**, even if they show up in a shared thread they're part of — being
  CC'd or mentioned doesn't mean it's their deliverable.
- **If legitimate tasks don't add up to a full week**, the right move is adding real documentation/write-up
  tasks for things already done but only informally (e.g. formalizing a verbal/chat analysis into a proper doc)
  — not inventing busywork or silently padding existing line items past what's realistic.

Present the "this week" table and ask if the user wants anything adjusted before they copy it into their actual
worklog tool — don't assume the first draft is final, since the time allocation always involves judgment calls
specific to that week's actual constraints (which team is blocking them, what got approved, etc.).

## Keeping your config out of git

If you fork/clone this skill and fill in your own company URL, project names, etc., consider splitting those
into a separate `config.md` (or just editing this file locally) and adding it to your personal `.gitignore` if
you ever version-control your `~/.claude/skills` directory — the placeholders above are exactly the kind of
company-internal detail you don't want to accidentally publish.
