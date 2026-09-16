"""Appends matched jobs to a date-named worksheet (e.g. "Sep16") in the
Excel workbook — one sheet per day, auto-created at local midnight. Sheets
are created in chronological order, so the oldest is always first in the
workbook; once more than MAX_DAILY_SHEETS exist, the oldest is dropped.

Direct openpyxl sheet management here (not pandas) — creating, finding, and
pruning individual worksheets in one workbook doesn't fit pandas' single-
table read/write model well.
"""

from datetime import datetime

from openpyxl import Workbook, load_workbook

import config

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
_DEFAULT_SHEET_NAME = "Sheet"


def _sheet_name_for_today() -> str:
    return datetime.now().strftime("%b%d")  # e.g. "Sep16"


def _load_or_create_workbook() -> Workbook:
    if config.EXCEL_FILE_PATH.exists():
        return load_workbook(config.EXCEL_FILE_PATH)
    return Workbook()


def _get_or_create_today_sheet(wb: Workbook):
    name = _sheet_name_for_today()
    if name in wb.sheetnames:
        return wb[name]

    ws = wb.create_sheet(title=name)
    ws.append(HEADERS)

    # A brand-new Workbook() always starts with one blank default sheet —
    # drop it now that a real dated sheet exists, but only if it's still
    # untouched (never remove it if it somehow has real data).
    default = wb[_DEFAULT_SHEET_NAME] if _DEFAULT_SHEET_NAME in wb.sheetnames else None
    if default is not None and default.max_row == 1 and default["A1"].value is None:
        del wb[_DEFAULT_SHEET_NAME]

    return ws


def _prune_old_sheets(wb: Workbook) -> None:
    names = wb.sheetnames
    excess = max(0, len(names) - MAX_DAILY_SHEETS)
    for name in names[:excess]:
        del wb[name]


def append_jobs(jobs: list[dict]) -> None:
    if not jobs:
        return

    wb = _load_or_create_workbook()
    ws = _get_or_create_today_sheet(wb)

    for job in jobs:
        ws.append(
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
        )

    _prune_old_sheets(wb)
    wb.save(config.EXCEL_FILE_PATH)
