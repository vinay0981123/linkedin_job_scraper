"""Appends matched jobs to a Google Sheet, mirroring excel_writer.py.

Uses a service account (gspread) — no browser OAuth consent flow, so it
works unattended. Any failure here is logged and swallowed: the local Excel
file (excel_writer.py) is the durable copy and must never be blocked by a
Sheets API hiccup.
"""

import logging

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
    "Job URL",
    "Scraped At",
]

_worksheet = None


def _get_worksheet():
    global _worksheet
    if _worksheet is not None:
        return _worksheet

    client = gspread.service_account(filename=str(config.GOOGLE_SERVICE_ACCOUNT_FILE))
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)

    try:
        ws = sheet.worksheet(config.GOOGLE_SHEET_WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(
            title=config.GOOGLE_SHEET_WORKSHEET_NAME, rows=1000, cols=len(HEADERS)
        )

    if not ws.row_values(1):
        ws.append_row(HEADERS)

    _worksheet = ws
    return ws


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _append_rows(ws, rows: list[list]) -> None:
    ws.append_rows(rows, value_input_option="RAW")


def append_jobs(jobs: list[dict]) -> None:
    """jobs: list of dicts with keys matching excel_writer.COLUMN_MAP."""
    if not jobs or not config.GOOGLE_SHEETS_ENABLED:
        return

    try:
        ws = _get_worksheet()
        rows = [
            [
                job["title"],
                job["company"],
                job["location"],
                job["posted_time"],
                job["matched_keywords"],
                job["url"],
                job["scraped_at"],
            ]
            for job in jobs
        ]
        _append_rows(ws, rows)
    except Exception:
        logger.exception("Failed to append jobs to Google Sheet — Excel copy is unaffected")
