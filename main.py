"""Continuously polls LinkedIn for jobs matching config.KEYWORDS in
config.LOCATIONS, posted within the last MAX_POSTED_AGE_MINUTES, requiring
at most YOUR_YEARS_OF_EXPERIENCE, and appends new matches to Excel/Sheets plus
a Telegram notification per job. Runs until interrupted (Ctrl+C).

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

from playwright.sync_api import Error as PlaywrightError

import config
import dedup_store
import excel_writer
import sheets_writer
import telegram_notifier
from browser_session import open_context
from experience_matcher import meets_experience_requirement
from keyword_matcher import build_search_query, matching_keywords
from location_matcher import is_relevant_location
from logging_setup import setup_logging
from scraper import build_search_url, fetch_job_details, posted_minutes_ago, scrape_jobs

logger = logging.getLogger(__name__)


def _jitter() -> None:
    time.sleep(random.uniform(config.MIN_INTER_REQUEST_DELAY, config.MAX_INTER_REQUEST_DELAY))


def run_cycle(page, keyword_query: str) -> int:
    new_jobs = []

    for city in config.LOCATIONS:
        url = build_search_url(keyword_query, city)

        try:
            jobs = scrape_jobs(page, url)
        except PlaywrightError:
            # The browser/page itself is gone (closed, crashed, etc.), not
            # just a flaky request — scrape_jobs already retried 3x before
            # giving up. Propagate so main() can recover the whole session,
            # instead of silently reporting "0 jobs" every cycle forever.
            raise
        except Exception:
            logger.exception("Scrape failed for %s", city)
            jobs = []

        for job in jobs:
            if dedup_store.has_seen(job["job_id"]):
                continue

            matched = matching_keywords(job["title"])
            if not matched:
                continue

            age_minutes = posted_minutes_ago(job["posted_time"])
            if age_minutes is not None and age_minutes > config.MAX_POSTED_AGE_MINUTES:
                # Card explicitly says too old — no need to spend a detail
                # page fetch confirming what we already know.
                continue

            if not is_relevant_location(job["location"]):
                continue

            # Everything free (title/age-if-known/location) has passed —
            # commit to this job now so a flaky detail fetch below never
            # causes it to be re-evaluated (and re-fetched) in a later cycle.
            dedup_store.mark_seen(job["job_id"])

            try:
                description, detail_posted_time = fetch_job_details(page, job["url"])
            except PlaywrightError:
                raise
            except Exception:
                logger.exception("Failed to fetch details for %s", job["url"])
                continue
            finally:
                _jitter()

            posted_time_display = job["posted_time"]
            if age_minutes is None:
                # Card showed no time badge at all (e.g. LinkedIn's own
                # auto-preview marked it "Viewed") — fall back to the
                # detail page's own indicator as the authoritative check.
                age_minutes = posted_minutes_ago(detail_posted_time)
                if age_minutes is None or age_minutes > config.MAX_POSTED_AGE_MINUTES:
                    logger.info(
                        "Rejected (too old on detail-page check, %s): %s",
                        detail_posted_time or "no time found",
                        job["url"],
                    )
                    continue
                posted_time_display = detail_posted_time

            qualifies, experience_display = meets_experience_requirement(
                description, config.YOUR_YEARS_OF_EXPERIENCE
            )
            if not qualifies:
                logger.info(
                    "Rejected (requires %s, you have %s): %s",
                    experience_display,
                    config.YOUR_YEARS_OF_EXPERIENCE,
                    job["url"],
                )
                continue

            new_jobs.append(
                {
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"] or city,
                    "posted_time": posted_time_display,
                    "matched_keywords": ", ".join(matched),
                    "expected_experience": experience_display,
                    "url": job["url"],
                    "scraped_at": job["scraped_at"],
                }
            )

        _jitter()

    excel_writer.append_jobs(new_jobs)
    sheets_writer.append_jobs(new_jobs)
    telegram_notifier.notify_new_jobs(new_jobs)
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

            try:
                found = run_cycle(page, keyword_query)
                logger.info(
                    "-> %s new matching job(s) saved to %s", found, config.EXCEL_FILE_PATH.name
                )
            except PlaywrightError:
                logger.exception(
                    "Browser session died (closed/crashed) — reopening automatically"
                )
                for cleanup in (context.close, playwright.stop):
                    try:
                        cleanup()
                    except Exception:
                        pass
                context, playwright = open_context()
                page = context.pages[0] if context.pages else context.new_page()
                logger.info("Browser session restored — resuming polling.")

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
