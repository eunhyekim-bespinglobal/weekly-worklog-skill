---
name: weekly-worklog
description: "Compile a weekly worklog entry (last week's completed work + this week's plan, time-boxed to a full work week, as a task/deliverable/hours table) by cross-referencing local Claude Code session logs, your team chat, and (via the bundled read-chrome-history.py) Chrome browsing history. Trigger this whenever the user mentions 'worklog', 'weekly report', asks what they did last week / should do this week, or it's the start of the week and they're preparing a status update. Always use this instead of starting from scratch — it encodes judgment calls about how to scope and time-box tasks that are easy to get wrong (padding blocked tasks, logging hours for work that can't start yet, etc)."
---

# Weekly worklog compiler

Many teams require a weekly status log — what got done, what's planned, broken into tasks with time estimates
that should add up to a full work week. This skill reconstructs that from three sources you don't manually track
in real time: your local Claude Code session history, your team chat tool, and your Chrome browsing history. It
can be invoked manually (e.g. every Monday) or wired to a local scheduled task — see "Optional: automating this
on a schedule" near the bottom, including several hard-won pitfalls if you try.

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

## Why three sources

No single source is enough. Local Claude Code sessions capture the *technical* work (debugging, code changes,
investigations) across your repos, but miss anything decided or requested over chat (meeting outcomes, approvals,
blockers, other people's asks of you) or done outside Claude Code entirely (cloud console clicks, doc/sheet edits,
internal tools). Chat captures the organizational context but not the technical substance or web-tool usage.
Browser history fills a lot of that last gap. Combine whichever are available — treat chat and browser history as
optional if you don't have `claude-in-chrome` (or an equivalent) connected; the skill is still useful with just
the local session logs.

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

## Step 2.5 — Browser history (optional)

Local session logs and chat both miss a lot of real work done in a browser: cloud console clicks, doc/sheet
edits, internal tools, one-off research. `chrome://history` itself is unreadable through most browser-automation
MCP tools (Chrome blocks extensions from scripting any `chrome://` page, regardless of how you navigate there —
don't waste time retrying that path). It's readable a different way: the history is a local SQLite file on disk.

Use the bundled `read-chrome-history.py` (next to this file) rather than writing ad hoc queries. It does the
file-locking-safe copy (Chrome locks the file while running), the query, and — importantly — mechanically strips
anything that looks like an OAuth/SSO/session token (auth-provider hosts, `code=`/`token=`/`state=`/etc. query
params, long or launcher-style query strings) *before that text ever reaches you*. That's deliberate: a script
that never writes a secret into its output can't leak it by mistake, whereas an LLM asked nicely not to repeat
one still can. It's also why headless/scheduled runs can safely use this specific script even though their
permission scope otherwise blocks general Bash/Python — see the automation section below.

Run it like this:

```
python ~/.claude/read-chrome-history.py --days <N> --out <path>
```

`--days N` should cover from the start of the range you're reconstructing through today, inclusive — e.g. for
"since Monday" on a Wednesday, that's `--days 3`. Read the output file, not the console (see the encoding pitfall
in the automation section — the same class of bug applies to any tool's output, not just Claude's). Once you're
done with it, clean up the same way you created it:

```
python ~/.claude/read-chrome-history.py --delete <the-same-path>
```

(`--delete` only removes files whose basename starts with `history_`, so it can't become a general-purpose
delete primitive even from a malformed argument.)

What's left in the output is de-duplicated and auth-noise-free but **not** filtered for personal-vs-work — apply
the same hard boundary as personal chat in Step 2 (never surface it, even in passing), and group by topic rather
than individual URL (a dozen visits to the same doc over an hour is one line of work, not twelve).

`find_active_history_file()` in the script looks in the standard Chrome profile locations for Windows, macOS, and
Linux and picks whichever profile was modified most recently — adjust it if your setup is unusual (e.g. a
non-default profile directory, or Chromium/Brave/Edge instead of Chrome).

## Step 3 — Compile

Once whichever of your sources were available are in, produce two things:

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

## Optional: automating this on a schedule

This skill ships without a wired-up automatic trigger, for the reason stated above: local filesystem + browser
session access, neither reachable from a cloud scheduler. If you want a *local* OS-level schedule (Windows Task
Scheduler, cron, launchd) to run it unattended, several pitfalls came up building and validating this for real —
against the *actual* scheduler, not just by running the wrapper script interactively, which hid two of these —
and are worth knowing before you try:

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
   Step 1's instruction to spawn a background summarizing Agent runs as-is in headless mode, the process has no
   "later" in which to receive that agent's completion and finish the report — it just silently gives up on that
   source. For a headless/scheduled run specifically, instruct the model to read files directly/synchronously
   (Grep/Read) instead of delegating to a background Agent, even though that's slower — reliability over
   parallelism when there's no ongoing session to deliver an async result into.
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
   treat this as a fatal error — this skill is written to fall back to local-session-logs + browser history and
   say so plainly in the output when this happens.

Validate any of this against the *real* scheduled task (e.g. `Start-ScheduledTask` on Windows), not just by
running the wrapper script yourself in an interactive terminal — several of the above only surfaced that way.

## Keeping your config out of git

If you fork/clone this skill and fill in your own company URL, project names, etc., consider splitting those
into a separate `config.md` (or just editing this file locally) and adding it to your personal `.gitignore` if
you ever version-control your `~/.claude/skills` directory — the placeholders above are exactly the kind of
company-internal detail you don't want to accidentally publish.
