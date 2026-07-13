"""
read-chrome-history.py — extract a day (or range) of Chrome browsing
history for the weekly-worklog / daily-worklog Claude Code skills.

Design goal: this is the ONLY thing headless/scheduled runs of those
skills are allowed to execute (see run-daily-worklog.ps1's --allowedTools,
scoped to this exact script path) — so it does the security-sensitive
part itself, deterministically, rather than leaving it to model judgment:

  - Copies the History file before reading (Chrome locks it while running).
  - Strips any URL that looks like it carries OAuth/SSO/SAML material
    (auth-provider hosts, or query params like code=/token=/state=) before
    it ever reaches the model's context — an LLM asked nicely not to repeat
    a secret can still slip; a URL that was never written to the output
    file can't leak it.
  - Cleans up its own temp copy on exit.

What it does NOT do: decide what's "personal" vs "work". That's inherently
judgment-based (a Naver search title alone doesn't self-label), so it's
left to the skill's Step 3 compile logic once it reads this script's
output — the same way Step 2 already filters personal chat.

Usage:
    python read-chrome-history.py [YYYY-MM-DD] [--days N] --out <path>
    python read-chrome-history.py --delete <path>

    YYYY-MM-DD   end date, defaults to today
    --days N     how many days back from that date to include (default 1)
    --out PATH   where to write the UTF-8 result file
    --delete PATH  clean up a previously-written output file instead of
                    generating a new one — same script, same allowlisted
                    command prefix, so a headless run that can't grant
                    itself a general `rm` can still tidy up after itself.
                    Only deletes files matching this script's own output
                    naming convention (basename starting with "history_"),
                    so this can't be turned into an arbitrary-file-delete
                    primitive even by a malformed/injected argument.
"""
import argparse
import datetime
import glob
import os
import platform
import re
import shutil
import sqlite3
import sys
import tempfile

AUTH_HOST_RE = re.compile(r"(okta\.com|keycloak|/oauth2/|/saml2/|/auth/realms/)", re.I)
AUTH_QUERY_RE = re.compile(
    r"[?&](code|state|token|session_state|id_token|access_token|client_secret|password|secret|SAMLRequest|Signature)=",
    re.I,
)
# These carry embedded session/connection tokens too (e.g. VDI/Citrix launchers)
# but don't use a recognizable param name, so they're handled separately:
# stripped down to base URL rather than dropped outright, since the fact of
# visiting them (e.g. "connected to LGE Cloud PC") is still useful signal.
LAUNCHER_RE = re.compile(r"(/vsclient/|\.ica\?|[?&]args=)", re.I)
LONG_QUERY_THRESHOLD = 100  # chars; long query strings are almost always tokens, not human intent

CHROME_EPOCH_OFFSET = 11644473600  # seconds between 1601-01-01 and 1970-01-01


def find_active_history_file() -> str:
    system = platform.system()
    if system == "Windows":
        base_dirs = [os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")]
    elif system == "Darwin":
        base_dirs = [os.path.expanduser("~/Library/Application Support/Google/Chrome")]
    else:
        base_dirs = [
            os.path.expanduser("~/.config/google-chrome"),
            os.path.expanduser("~/.config/chromium"),
        ]

    candidates = []
    for base in base_dirs:
        candidates.extend(glob.glob(os.path.join(base, "*", "History")))
    if not candidates:
        raise SystemExit("No Chrome History file found under " + " or ".join(base_dirs))
    # Several profiles can exist; the one most recently written to is the
    # one actually in use.
    return max(candidates, key=os.path.getmtime)


def to_chrome_time(dt: datetime.datetime) -> int:
    return int((dt.timestamp() + CHROME_EPOCH_OFFSET) * 1_000_000)


def from_chrome_time(chrome_time: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(chrome_time / 1_000_000 - CHROME_EPOCH_OFFSET)


def is_auth_noise(url: str) -> bool:
    return bool(AUTH_HOST_RE.search(url) or AUTH_QUERY_RE.search(url))


def strip_query_if_token_like(url: str) -> str:
    """Keep the URL as-is unless it looks like it's carrying a session/
    connection token in an unnamed param — then keep only scheme+host+path."""
    query_part = url.split("?", 1)[1] if "?" in url else ""
    if LAUNCHER_RE.search(url) or len(query_part) > LONG_QUERY_THRESHOLD:
        return url.split("?")[0].split("#")[0]
    return url


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?", default=datetime.date.today().isoformat())
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--out")
    ap.add_argument("--delete")
    args = ap.parse_args()

    if args.delete:
        target = os.path.abspath(args.delete)
        if not os.path.basename(target).startswith("history_"):
            raise SystemExit(
                "Refusing to delete " + target + " — only this script's own "
                "history_*.txt output files can be removed this way."
            )
        if os.path.exists(target):
            os.remove(target)
            print(f"deleted {target}")
        else:
            print(f"{target} already gone, nothing to do")
        return

    if not args.out:
        raise SystemExit("--out is required unless --delete is given")

    end_date = datetime.date.fromisoformat(args.date)
    start_date = end_date - datetime.timedelta(days=args.days - 1)

    src = find_active_history_file()

    with tempfile.TemporaryDirectory() as tmp:
        db_copy = os.path.join(tmp, "History")
        shutil.copy2(src, db_copy)

        conn = sqlite3.connect(db_copy)
        cur = conn.cursor()

        start_ct = to_chrome_time(datetime.datetime.combine(start_date, datetime.time.min))
        end_ct = to_chrome_time(datetime.datetime.combine(end_date, datetime.time.max))

        cur.execute(
            """
            SELECT visits.visit_time, urls.url, urls.title
            FROM visits JOIN urls ON visits.url = urls.id
            WHERE visits.visit_time BETWEEN ? AND ?
            ORDER BY visits.visit_time ASC
            """,
            (start_ct, end_ct),
        )
        rows = cur.fetchall()
        conn.close()
    # `tmp`, including the History copy, is deleted automatically here.

    seen = set()
    lines = []
    dropped_auth = 0
    for visit_time, url, title in rows:
        if is_auth_noise(url):
            dropped_auth += 1
            continue
        url = strip_query_if_token_like(url)
        ts = from_chrome_time(visit_time)
        minute_key = ts.strftime("%Y-%m-%d %H:%M")
        dedup_key = (minute_key, url)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        lines.append(f"{minute_key} | {title or ''} | {url}")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(
            f"# Chrome history {start_date} ~ {end_date} "
            f"({len(lines)} entries, {dropped_auth} auth/SSO URLs stripped)\n\n"
        )
        f.write("\n".join(lines))
        f.write("\n")

    print(f"wrote {len(lines)} entries ({dropped_auth} auth URLs dropped) to {args.out}")


if __name__ == "__main__":
    main()
