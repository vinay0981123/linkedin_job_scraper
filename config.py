"""Central configuration. Edit freely — no code changes needed for tuning."""

from pathlib import Path

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
# within a cycle, to avoid a fixed, bot-like request cadence.
MIN_INTER_REQUEST_DELAY = 4
MAX_INTER_REQUEST_DELAY = 12

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
}

# Output files
EXCEL_FILE_PATH = BASE_DIR / "linkedin_jobs.xlsx"
DEDUP_DB_PATH = BASE_DIR / "seen_jobs.db"
LOG_FILE_PATH = BASE_DIR / "scraper.log"

# Google Sheets — mirrors the Excel output. Off by default; flip to True once
# you've created a service account, shared the target sheet with it as
# Editor, and filled in GOOGLE_SHEET_ID below.
GOOGLE_SHEETS_ENABLED = True
GOOGLE_SERVICE_ACCOUNT_FILE = BASE_DIR / "google_service_account.json"
GOOGLE_SHEET_ID = "1o98uYDvhnxNJMhUeSJHeoAb9URwk0IeId3ygNfvJjqk"
GOOGLE_SHEET_WORKSHEET_NAME = "Jobs"

# WhatsApp notifications via CallMeBot's free personal-use API. Off by
# default; flip to True once you've messaged the CallMeBot bot number and
# received your API key (see callmebot.com/blog/free-api-whatsapp-messages).
WHATSAPP_ENABLED = False
CALLMEBOT_PHONE = ""  # your WhatsApp number with country code, e.g. "+91XXXXXXXXXX"
CALLMEBOT_APIKEY = ""  # from the "API Activated..." message CallMeBot sends you

# Persistent Chromium profile dir — log in here once manually, every later
# run reuses the saved session automatically.
BROWSER_PROFILE_DIR = BASE_DIR / "browser_profile"

# Headed (visible) but launched minimized/off to the side — closer to normal
# browsing than headless, and lets you step in for a manual login/checkpoint.
HEADLESS = False
