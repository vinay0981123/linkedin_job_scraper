"""Continuously polls LinkedIn for jobs matching config.KEYWORDS in
config.LOCATIONS, posted within the last TIME_POSTED_RANGE_SECONDS, and
appends new matches to an Excel file. Runs until interrupted (Ctrl+C).

Setup (once):
    pip install -r requirements.txt
    playwright install chromium
    python3 main.py          # log in manually when the browser opens

Run:
    python3 main.py
"""

import logging
import random
import time
from datetime import datetime, timezone

import config
import dedup_store
import excel_writer
import sheets_writer
import whatsapp_notifier
from browser_session import open_context
from keyword_matcher import build_search_query, matching_keywords
from logging_setup import setup_logging
from scraper import build_search_url, scrape_jobs

logger = logging.getLogger(__name__)


def run_cycle(page, keyword_query: str) -> int:
    new_jobs = []

    for city in config.LOCATIONS:
        url = build_search_url(keyword_query, city)

        try:
            jobs = scrape_jobs(page, url)
        except Exception:
            logger.exception("Scrape failed for %s", city)
            jobs = []

        for job in jobs:
            if dedup_store.has_seen(job["job_id"]):
                continue

            matched = matching_keywords(job["title"])
            if not matched:
                continue

            dedup_store.mark_seen(job["job_id"])
            new_jobs.append(
                {
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"] or city,
                    "posted_time": job["posted_time"],
                    "matched_keywords": ", ".join(matched),
                    "url": job["url"],
                    "scraped_at": job["scraped_at"],
                }
            )

        delay = random.uniform(config.MIN_INTER_REQUEST_DELAY, config.MAX_INTER_REQUEST_DELAY)
        time.sleep(delay)

    excel_writer.append_jobs(new_jobs)
    sheets_writer.append_jobs(new_jobs)
    whatsapp_notifier.notify_new_jobs(new_jobs)
    return len(new_jobs)


def main():
    setup_logging()
    dedup_store.init_db()
    keyword_query = build_search_query()

    context, playwright = open_context()
    page = context.pages[0] if context.pages else context.new_page()

    logger.info("Search query: %s", keyword_query)
    logger.info("Cities: %s", ", ".join(config.LOCATIONS))
    logger.info("Polling every %ss. Ctrl+C to stop.", config.POLL_INTERVAL_SECONDS)

    try:
        while True:
            started = datetime.now(timezone.utc)
            logger.info("Starting poll cycle...")

            found = run_cycle(page, keyword_query)
            logger.info("-> %s new matching job(s) saved to %s", found, config.EXCEL_FILE_PATH.name)

            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            sleep_for = max(0, config.POLL_INTERVAL_SECONDS - elapsed)
            time.sleep(sleep_for)
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        context.close()
        playwright.stop()


if __name__ == "__main__":
    main()
