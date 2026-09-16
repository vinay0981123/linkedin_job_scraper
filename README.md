# LinkedIn Job Scraper

Continuously polls LinkedIn for newly posted jobs matching a set of title
keywords, filters them down to genuinely relevant, fresh, in-range-experience
postings, and pushes matches to Google Sheets and Telegram.

No AI/LLM involved anywhere in the pipeline — matching and filtering are all
plain keyword/regex logic.

## What it does

Every 5 minutes, for each configured city:

1. Builds a LinkedIn job search URL (keywords, location, time-posted filter,
   verified-jobs-only) and scrapes the results with a real, logged-in
   browser session (Playwright).
2. Filters each result through, in order:
   - **Title match** against your configured keyword list
   - **Freshness** — strictly enforced locally (not just LinkedIn's own loose
     `f_TPR` filter), with a fallback that checks a job's own detail page
     when the search card shows no time badge at all (LinkedIn auto-previews
     the top result, which suppresses its badge)
   - **Location relevance** — your target cities, or Remote
   - **Experience requirement** — parses the actual years-of-experience
     text from the full job description (handles "2 to 6 years", "2-6",
     "3+ years", "minimum 3 years", etc.) and drops postings that need more
     than you have
3. Writes every surviving match to:
   - A Google Sheet, one worksheet per day (`Sep16`, `Sep17`, ...), rolling
     7-day window
   - Telegram, one message per job

## Setup

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Log in to LinkedIn

```bash
python3 main.py
```

A browser window opens (first run only — set `HEADLESS = False` in
`config.py` if it's currently `True`). Log in manually, including any 2FA.
The session is saved to `browser_profile/` and reused on every later run —
no credentials are ever stored in code.

### 3. Configure secrets

```bash
cp secrets_local.py.example secrets_local.py
```

Fill in `secrets_local.py` (gitignored, never committed):

- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` — create a bot via
  [@BotFather](https://t.me/BotFather), message it once, then fetch
  `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your chat id.
- `GOOGLE_SHEET_ID` — from your target sheet's URL
  (`.../spreadsheets/d/<THIS_PART>/edit`).

### 4. Google Sheets access

1. Create a Google Cloud project, enable the **Google Sheets API** and
   **Google Drive API**.
2. Create a **Service Account**, generate a JSON key, save it as
   `google_service_account.json` in this directory (gitignored).
3. Share your target Google Sheet with the service account's
   `client_email` (from the JSON key) as **Editor**.

## Configuration

Everything tunable lives in `config.py`:

| Setting | Purpose |
|---|---|
| `KEYWORDS` | Job title keywords to match |
| `LOCATIONS` | Cities to search |
| `POLL_INTERVAL_SECONDS` | How often to run a full cycle |
| `MAX_POSTED_AGE_MINUTES` | Strict local freshness cutoff |
| `YOUR_YEARS_OF_EXPERIENCE` | Postings requiring more than this are dropped |
| `SEARCH_DISTANCE_MILES` | LinkedIn search radius (local location check is the real enforcement) |
| `HEADLESS` | Run without a visible browser window |
| `GOOGLE_SHEETS_ENABLED` / `TELEGRAM_ENABLED` | Toggle each output independently |

## Running

```bash
source .venv/bin/activate
python3 main.py
```

Runs until stopped with `Ctrl+C`. If the browser session ever closes
unexpectedly, it's detected and automatically relaunched. Logs go to
`application_log.log` (auto-rotates at 100MB, keeps 3 backups) and the
console. Dedup state lives in `seen.db`.

## Running via Docker

The published image (`vinay098/monitor`) contains only the
code — never `browser_profile/`, `secrets_local.py`, or
`google_service_account.json`. Those are mounted in at runtime instead
(see `docker-compose.yml`), so the image itself is safe to publish.

You still need to log in **outside Docker first** — there's no way to do
the interactive LinkedIn login (2FA, etc.) from inside a headless
container:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && playwright install chromium
python3 main.py   # log in, then Ctrl+C once "LinkedIn session ready" appears
```

That creates `browser_profile/`. Then, with `secrets_local.py` and
`google_service_account.json` also in place (see Setup above):

```bash
# these must exist as files before the first `up`, or Docker creates
# them as empty directories instead when bind-mounting
touch seen.db application_log.log

docker compose up -d
docker compose logs -f
```

## Notes

- LinkedIn's Terms of Service prohibit automated scraping. This is built for
  personal, low-volume, non-bulk use against your own account, with
  deliberate rate-limiting (jittered delays, no aggressive polling) — but
  there's inherent risk of account restriction with any automation, however
  careful. Use at your own discretion.
- `browser_profile/`, `secrets_local.py`, and `google_service_account.json`
  hold live credentials/session state — never commit them (already
  gitignored).
