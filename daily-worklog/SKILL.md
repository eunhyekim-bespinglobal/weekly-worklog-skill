---
name: daily-worklog
description: "Compile a daily worklog entry (today's completed work only, time-boxed to a full work day, as a task/hours table) by cross-referencing local Claude Code session logs, your team chat, and (via the bundled read-chrome-history.py) Chrome browsing history. Trigger this whenever the user mentions 'daily worklog', 'daily report', asks what they did today, or it's late afternoon and they're preparing an end-of-day status update. This is the daily sibling of the weekly-worklog skill — same sources, much narrower scope: one day, retrospective only, no forward-looking plan."
---

# Daily worklog compiler

Some teams want a worklog entry every day, not just weekly — "what did I do today," logged before you leave.
This is the daily sibling of `weekly-worklog`: same three sources (local Claude Code session history, team chat,
and Chrome browsing history), narrowed to a single day, with a simpler output. If you haven't set up
`weekly-worklog` yet, read that skill's SKILL.md first — the setup placeholders and source-gathering approach are
shared.

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

## Step 2.5 — Browser history (today only, optional)

Same approach as `weekly-worklog` Step 2.5, using the bundled `read-chrome-history.py` (next to this file) scoped
to today only:

```
python ~/.claude/read-chrome-history.py --out <path>
```

(no `--days` needed — it defaults to today.) Read the SKILL.md for `weekly-worklog` for the full rationale — why
a script handles this instead of ad hoc queries, what it strips before you ever see it, and how to clean up
afterward (`--delete <same-path>`). Same personal-vs-work judgment call applies here as it does to chat: never
surface personal browsing, even in passing, and group by topic rather than individual URL.

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
want a *local* OS-level schedule (Windows Task Scheduler, cron, launchd) to run this unattended, several pitfalls
came up building and validating this for real — against the *actual* scheduler, not just by running the wrapper
script interactively, which hid two of these — and are worth knowing before you try:

1. **Native console output encoding is unreliable across contexts.** A CLI's effective stdout encoding can differ
   depending on whether a console is attached — tuning PowerShell's `$OutputEncoding` and capturing output through
   its native-command pipeline (`$result = & claude.exe ... 2>&1`) can work when you test the wrapper script from
   an interactive shell, then produce mojibake on the *actual* scheduled run, because Task Scheduler launches with
   no console attached and the effective encoding differs. Don't route through PowerShell's native-command string
   pipeline at all: use `Start-Process` with real OS-level file redirection (`-RedirectStandardOutput`/
   `-RedirectStandardError`, raw bytes, no PowerShell decoding at capture time), then explicitly read the result
   back with a fixed encoding (`Get-Content -Raw -Encoding UTF8`) — modern CLIs generally write UTF-8 to a
   redirected/piped stream regardless of console state, so decoding it yourself removes the ambiguity entirely.
2. **`Start-Process -ArgumentList` doesn't reliably quote array elements containing spaces** (confirmed on Windows
   PowerShell 5.1). A multi-word prompt passed as one array element can get silently re-split, and text inside it
   that happens to look like a flag (e.g. an example command containing `--out <path>`) gets parsed by the target
   program as a real argument it doesn't recognize. Build one properly-escaped Windows command-line string
   yourself (standard MSVCRT argv-quoting: wrap in quotes, double backslashes before a literal quote or at the
   end of the string) and pass that single string to `-ArgumentList` instead of an array.
3. **Set an explicit working directory.** A process launched by Task Scheduler (or by `Start-Process` generally,
   if you don't specify one) can default to somewhere like `C:\Windows\System32` rather than your user profile —
   pass `-WorkingDirectory` explicitly, or a tool that resolves relative paths may end up rooted somewhere your
   home-directory files aren't reachable from.
4. **A one-shot headless invocation (`claude -p "..."`) can't receive an async background-task notification.** If
   an instruction to spawn a background summarizing Agent runs as-is in headless mode (daily-worklog's Step 1
   avoids this for typical single-day scope, but can still hit it on an unusually busy day), the process has no
   "later" in which to receive that agent's completion — it just silently gives up on that source. For a
   headless/scheduled run, instruct the model to read files directly/synchronously (Grep/Read) instead of
   delegating to a background Agent, even though that's slower — reliability over parallelism when there's no
   ongoing session to deliver an async result into.
5. **Unattended permission handling.** A headless run has no one to approve tool-use prompts, so it needs some
   form of non-interactive permission — but reach for a scoped allowlist (`--allowedTools "Read Grep Agent ..."`)
   rather than blanket-bypassing permission checks. If you bundle a script for a sensitive step (like browser
   history above), pin the allowlist to that script's *exact* invocation form, not a loose pattern: the Bash tool
   commonly runs through something like Git Bash on Windows, which uses POSIX-style paths (`/c/Users/...`), not
   Windows backslash paths, so an allowlist pattern built from a Windows-style path silently never matches and
   the call just hangs waiting for an approval that never comes. Put the literal, pre-computed command directly in
   the prompt — including a concrete output file path, not a placeholder like `<path>` for the model to fill in,
   which invites it to invent a filename that doesn't match your allowlist pattern or your cleanup script's
   expected naming.
6. **Browser-extension chat MCPs typically allow only one connected session.** If an interactive session already
   holds the connection, a separate scheduled/headless process usually can't also attach to check chat. Don't
   treat this as a fatal error — both skills are written to fall back to local-session-logs + browser history and
   say so plainly in the output when this happens.

Validate any of this against the *real* scheduled task (e.g. `Start-ScheduledTask` on Windows), not just by
running the wrapper script yourself in an interactive terminal — several of the above only surfaced that way.
