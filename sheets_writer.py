"""Appends matched jobs to a date-named worksheet (e.g. "Sep16") in the
Google Sheet, mirroring excel_writer.py — one sheet per day, auto-created
at local midnight, with only the last MAX_DAILY_SHEETS kept.

Uses a service account (gspread) — no browser OAuth consent flow, so it
works unattended. Any failure here is logged and swallowed: the local Excel
file (excel_writer.py) is the durable copy and must never be blocked by a
Sheets API hiccup.
"""

import logging
import re
from datetime import datetime

import gspread
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

import config

logger = logging.getLogger(__name__)

HEADERS = [
    "Job Title",
    "Company",
    "Location",
    "Posted Time",
    "Matched Keywords",
    "Expected Experience",
    "Job URL",
    "Scraped At",
]

MAX_DAILY_SHEETS = 7
_DATE_SHEET_RE = re.compile(r"^[A-Z][a-z]{2}\d{2}$")  # e.g. "Sep16"

_spreadsheet = None


def _get_spreadsheet():
    global _spreadsheet
    if _spreadsheet is None:
        client = gspread.service_account(filename=str(config.GOOGLE_SERVICE_ACCOUNT_FILE))
        _spreadsheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    return _spreadsheet


def _sheet_name_for_today() -> str:
    return datetime.now().strftime("%b%d")


def _is_date_sheet(title: str) -> bool:
    return bool(_DATE_SHEET_RE.match(title))


def _has_no_real_data(ws) -> bool:
    """True if the sheet has at most a header row — no actual data rows.
    get_all_values() returns [[]] (not []) for a truly blank sheet, so blank
    rows must be filtered out before counting, not just checked for falsy."""
    values = ws.get_all_values()
    non_blank_rows = [row for row in values if any(cell.strip() for cell in row)]
    return len(non_blank_rows) <= 1


def _get_or_create_today_worksheet(spreadsheet):
    name = _sheet_name_for_today()
    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        pass

    ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=len(HEADERS))
    ws.append_row(HEADERS)

    # One-time cleanup: Google's auto-created blank default sheet, and the
    # old static "Jobs" sheet from before per-day rotation existed. Only
    # ever removes sheets with no real data (header row or fully blank).
    for stale_name in ("Sheet1", "Sheet", "Jobs"):
        try:
            stale_ws = spreadsheet.worksheet(stale_name)
        except gspread.WorksheetNotFound:
            continue
        if _has_no_real_data(stale_ws):
            spreadsheet.del_worksheet(stale_ws)

    return ws


def _prune_old_worksheets(spreadsheet) -> None:
    # Only ever touches our own date-named sheets — never a sheet the user
    # added or renamed by hand.
    date_sheets = [ws for ws in spreadsheet.worksheets() if _is_date_sheet(ws.title)]
    excess = max(0, len(date_sheets) - MAX_DAILY_SHEETS)
    for ws in date_sheets[:excess]:
        spreadsheet.del_worksheet(ws)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _append_rows(ws, rows: list[list]) -> None:
    ws.append_rows(rows, value_input_option="RAW")


def append_jobs(jobs: list[dict]) -> None:
    """jobs: list of dicts with keys matching excel_writer's job dict shape."""
    if not jobs or not config.GOOGLE_SHEETS_ENABLED:
        return

    try:
        spreadsheet = _get_spreadsheet()
        ws = _get_or_create_today_worksheet(spreadsheet)
        rows = [
            [
                job["title"],
                job["company"],
                job["location"],
                job["posted_time"],
                job["matched_keywords"],
                job["expected_experience"],
                job["url"],
                job["scraped_at"],
            ]
            for job in jobs
        ]
        _append_rows(ws, rows)
        _prune_old_worksheets(spreadsheet)
    except Exception:
        logger.exception("Failed to append jobs to Google Sheet — Excel copy is unaffected")
