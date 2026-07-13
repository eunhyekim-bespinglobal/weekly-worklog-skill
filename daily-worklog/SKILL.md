---
name: daily-worklog
description: "Compile a daily worklog entry (today's completed work only, time-boxed to a full work day, as a task/hours table) by cross-referencing local Claude Code session logs and your team chat. Trigger this whenever the user mentions 'daily worklog', 'daily report', asks what they did today, or it's late afternoon and they're preparing an end-of-day status update. This is the daily sibling of the weekly-worklog skill — same sources, much narrower scope: one day, retrospective only, no forward-looking plan."
---

# Daily worklog compiler

Some teams want a worklog entry every day, not just weekly — "what did I do today," logged before you leave.
This is the daily sibling of `weekly-worklog`: same two sources (local Claude Code session history + optionally
team chat), narrowed to a single day, with a simpler output. If you haven't set up `weekly-worklog` yet, read
that skill's SKILL.md first — the setup placeholders and source-gathering approach are shared.

## How this differs from weekly-worklog

| | weekly-worklog | daily-worklog |
|---|---|---|
| Date range | start of week through today | today only (midnight → now) |
| Output | "last week" summary + "this week" plan table | one table only, retrospective |
| Columns | task / deliverable / hours | task / hours |
| Hours sum to | a full work week (default 40) | a full work day (default 8) |
| Forward-looking? | yes, includes a plan for the week ahead | no — today's log doesn't plan tomorrow |

## Setup

Same placeholders as `weekly-worklog/SKILL.md` (`<YOUR_WORKLOG_URL>`, `<YOUR_WORKLOG_FORMAT>`, `<YOUR_CHAT_TOOL>`,
`<YOUR_PRIMARY_WORK_CONTEXT>`) — if you've already configured that skill, use the same values here. The only
thing specific to this skill is your daily hours target (default assumption: 8h/day); adjust if your team's
worklog tool expects something else.

## Step 1 — Local session logs (today only)

```
find ~/.claude/projects -name "*.jsonl" -newermt "$(date +%Y-%m-%d) 00:00:00" ! -path "*/subagents/*"
```

Exclude the current session's own transcript. Group by project the same way as `weekly-worklog`. A single day is
usually few enough files to read directly — only spawn a background summarizing Agent if there are many large
files, same threshold as the weekly version.

## Step 2 — Team chat (today only, optional)

Same approach as `weekly-worklog` Step 2, scoped to today's messages. Skip automated-feed channels and personal/
casual chats; never surface personal content about the user or coworkers, even in passing.

## Step 3 — Compile

One table, exactly two columns, hours summing to a full work day (default 8):

| Task | Hours |
|---|---|

This is retrospective, so there's less judgment-call complexity than the weekly version, but a few things still
matter:

- **Log actual hands-on time, not wall-clock time spent waiting.** If part of the day went to waiting on someone
  else, only the following-up/coordinating time counts — same principle as weekly-worklog's external-approval
  rule.
- **Don't merge unrelated work into one vague line to save space.** Sub-hour granularity is fine here, unlike the
  weekly table where it usually isn't worth tracking.
- **If the sources don't add up to a full day, don't silently stretch line items to fill the gap.** Say so, and
  flag it for the user to check (meetings, offline work, work in a tool this skill can't see). This is the one
  place daily-worklog should *not* blindly force the total the way weekly-worklog does — a single day's shortfall
  is usually a real visibility gap, not something to paper over with padding.

Present the table and ask if anything needs adjusting before it goes into the actual worklog tool — unless this
is a scheduled/headless run (see below), in which case just output the best draft with caveats noted inline
(e.g. "chat not checked" or "under 8h, please verify").

## Optional: automating this on a schedule

Neither of these skills ships wired to an automatic trigger, because both depend on local filesystem access and
(for the chat step) an actively logged-in browser session — a cloud-hosted scheduler can't reach either. If you
want a *local* OS-level schedule (Windows Task Scheduler, cron, launchd) to run this unattended, three pitfalls
came up building this for real and are worth knowing before you try:

1. **Native console output encoding.** Some CLI runtimes (Claude Code's included) switch to UTF-16 output once
   stdout is redirected/non-interactive. On Windows PowerShell 5.1, the default `$OutputEncoding` used to decode
   a native command's output is single-byte (`us-ascii`), which mangles anything non-ASCII into garbage. Set
   `$OutputEncoding = [System.Text.Encoding]::Unicode` before invoking the CLI, and capture output through the
   pipeline (`$result = & claude.exe ... 2>&1`) rather than raw stream redirection (`*>>`), which bypasses
   decoding entirely.
2. **Unattended permission handling.** A headless run has no one to approve tool-use prompts, so it needs some
   form of non-interactive permission — but reach for a scoped allowlist (`--allowedTools "Read Grep Agent ..."`)
   rather than blanket-bypassing permission checks. These skills only need to read files and browse chat to
   produce a report; there's no reason an unattended run should be able to edit or execute arbitrary commands.
3. **Browser-extension chat MCPs typically allow only one connected session.** If an interactive session already
   holds the connection, a separate scheduled/headless process usually can't also attach to check chat. Don't
   treat this as a fatal error — both skills are written to fall back to local-session-logs-only and say so
   plainly in the output when this happens.
