"""Central configuration. Edit freely — no code changes needed for tuning.

Real credentials (Telegram token, Sheet ID) live in secrets_local.py, which
is gitignored and never committed — see secrets_local.py.example.
"""

from pathlib import Path

import secrets_local

BASE_DIR = Path(__file__).resolve().parent

# Job title keywords to match against scraped job titles (case-insensitive,
# word-boundary match). Edit this list any time — it also feeds the LinkedIn
# search query built in scraper.py.
KEYWORDS = [
    "DevOps Engineer",
    "Site Reliability Engineer",
    "SRE",
    "Cloud Engineer",
    "AWS Engineer",
    "AWS DevOps Engineer",
    "Platform Engineer",
    "Infrastructure Engineer",
    "Kubernetes Engineer",
    "Cloud Infrastructure Engineer",
]

# Cities to search — passed straight to LinkedIn's `location=` search param,
# which it resolves server-side (no geoId lookup needed).
LOCATIONS = [
    "Noida, Uttar Pradesh, India",
    "Greater Noida, Uttar Pradesh, India",
    "Gurugram, Haryana, India",
    "New Delhi, Delhi, India",
]

# How often to run a full poll cycle (all cities), in seconds.
POLL_INTERVAL_SECONDS = 5 * 60

# LinkedIn f_TPR window (seconds since posting) — kept wider than the poll
# interval so jobs aren't missed between cycles due to overlap gaps.
TIME_POSTED_RANGE_SECONDS = 15 * 60

# Random extra delay range (seconds) inserted between per-city searches
# within a cycle, to avoid a fixed, bot-like request cadence. Also reused
# between per-job description fetches (see YOUR_YEARS_OF_EXPERIENCE below).
MIN_INTER_REQUEST_DELAY = 4
MAX_INTER_REQUEST_DELAY = 12

# LinkedIn's default search radius (~25mi) can exclude genuinely relevant
# jobs pinned slightly outside a city center. Cast a wider net here, and
# rely on location_matcher.py's keyword check (against the cities above,
# or "Remote") as the real enforcement of relevance — not this radius.
SEARCH_DISTANCE_MILES = 75

# Extra LinkedIn search filters, merged into every search URL as-is.
# f_VJ=true (verified jobs only) is on by default — filters out likely
# scam/fake postings, which matters more than it costs in result count.
# Other filters you can add here if you want to narrow results further:
#   f_E    experience level: 1=Intern 2=Entry 3=Associate 4=Mid-Senior 5=Director 6=Executive
#          (comma-separated for multiple, e.g. "4,5")
#   f_JT   job type: F=Full-time P=Part-time C=Contract T=Temporary I=Intern V=Volunteer
#   f_WT   workplace: 1=On-site 2=Remote 3=Hybrid (comma-separated for multiple)
#   f_AL   "true" = actively hiring companies only
#   f_EA   "true" = Easy Apply only
EXTRA_SEARCH_FILTERS = {
    "f_VJ": "true",
    "distance": str(SEARCH_DISTANCE_MILES),
}

# LinkedIn's own f_TPR time filter is a soft target, not a hard guarantee —
# it can backfill with older postings when very-fresh ones are scarce. This
# is the real, strictly-enforced cutoff: a job whose displayed "posted time"
# parses to more than this many minutes old is dropped, no exceptions.
MAX_POSTED_AGE_MINUTES = 20

# Your actual years of experience. A posting's minimum required years
# (parsed from its full description via experience_matcher.py) must not
# exceed this to be kept — e.g. "2-6 years" or "3+ years" both qualify at
# YOUR_YEARS_OF_EXPERIENCE=4, but "5+ years" doesn't. A posting that
# doesn't state a requirement at all is always kept.
YOUR_YEARS_OF_EXPERIENCE = 4

# Output files
EXCEL_FILE_PATH = BASE_DIR / "linkedin_jobs.xlsx"
DEDUP_DB_PATH = BASE_DIR / "seen_jobs.db"
LOG_FILE_PATH = BASE_DIR / "scraper.log"

# Log auto-rotates once it hits this size, keeping LOG_BACKUP_COUNT old
# files (scraper.log.1, .2, ...) before the oldest is deleted — bounds disk
# usage instead of growing forever over a long-running process.
LOG_MAX_BYTES = 100 * 1024 * 1024  # 100MB
LOG_BACKUP_COUNT = 3

# Google Sheets — mirrors the Excel output. The service account and sheet
# sharing are already set up; GOOGLE_SERVICE_ACCOUNT_FILE just needs a valid
# key file present (see setup notes if it's missing).
GOOGLE_SHEETS_ENABLED = True
GOOGLE_SERVICE_ACCOUNT_FILE = BASE_DIR / "google_service_account.json"
GOOGLE_SHEET_ID = secrets_local.GOOGLE_SHEET_ID

# Telegram notifications via the official Bot API (free, no capacity limits,
# no third-party relay).
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = secrets_local.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = secrets_local.TELEGRAM_CHAT_ID

# Persistent Chromium profile dir — log in here once manually, every later
# run reuses the saved session automatically.
BROWSER_PROFILE_DIR = BASE_DIR / "browser_profile"

# Headless — Playwright's modern Chromium headless mode shares the same
# rendering engine as headed (unlike the old, easily-fingerprinted headless
# mode), and browser_session.py applies stealth patches + platform-
# consistency fixes on top. Set to False if you ever need to log in again —
# headless has no visible window for that (browser_session.py enforces this).
HEADLESS = True
