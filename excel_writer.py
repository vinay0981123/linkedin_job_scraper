"""Appends matched jobs to an Excel workbook, creating it with headers on
first use. Reads/writes the workbook once per poll cycle (not once per job)."""

import pandas as pd

import config

COLUMN_MAP = {
    "title": "Job Title",
    "company": "Company",
    "location": "Location",
    "posted_time": "Posted Time",
    "matched_keywords": "Matched Keywords",
    "url": "Job URL",
    "scraped_at": "Scraped At",
}


def append_jobs(jobs: list[dict]) -> None:
    """jobs: list of dicts with keys matching COLUMN_MAP (snake_case)."""
    if not jobs:
        return

    new_df = pd.DataFrame(jobs).rename(columns=COLUMN_MAP)[list(COLUMN_MAP.values())]

    if config.EXCEL_FILE_PATH.exists():
        existing_df = pd.read_excel(config.EXCEL_FILE_PATH, engine="openpyxl")
        combined = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined = new_df

    combined.to_excel(config.EXCEL_FILE_PATH, index=False, engine="openpyxl")
