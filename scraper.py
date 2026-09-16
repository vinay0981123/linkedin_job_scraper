"""Builds LinkedIn "just posted" search URLs and extracts job cards from the
results page.

Playwright handles navigation/scrolling (needed for the JS-rendered,
lazy-loaded job list); once the page is loaded, the rendered HTML is handed
to BeautifulSoup for extraction — plain, testable parsing instead of many
round-trip Playwright locator calls per card.

NOTE ON FRAGILITY: LinkedIn changes its DOM/class names periodically. The
selectors below are the current (2026) authenticated jobs-search layout. If
scraping starts returning zero results, first check (with a visible browser)
whether these selectors still match — that's the most likely breakage point,
not the rest of the pipeline.
"""

import logging
import re
import urllib.parse
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import config

logger = logging.getLogger(__name__)

SEARCH_BASE = "https://www.linkedin.com/jobs/search/"

_POSTED_TIME_RE = re.compile(r"\b\d+\s+(minute|hour|day|week|month)s?\s+ago\b", re.IGNORECASE)


def build_search_url(keyword_query: str, location: str) -> str:
    params = {
        "keywords": keyword_query,
        "location": location,
        "f_TPR": f"r{config.TIME_POSTED_RANGE_SECONDS}",
        "sortBy": "DD",  # date descending — newest first
        **config.EXTRA_SEARCH_FILTERS,
    }
    return f"{SEARCH_BASE}?{urllib.parse.urlencode(params)}"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    retry=retry_if_exception_type((PlaywrightTimeoutError, PlaywrightError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _load_search_results(page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    page.wait_for_timeout(2000)

    # LinkedIn lazy-loads job cards as the results pane scrolls.
    for _ in range(4):
        page.mouse.wheel(0, 1500)
        page.wait_for_timeout(800)


def scrape_jobs(page, url: str) -> list[dict]:
    _load_search_results(page, url)
    return parse_job_cards(page.content())


def parse_job_cards(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    scraped_at = datetime.now(timezone.utc).isoformat()

    results = []
    for card in soup.select("li[data-occludable-job-id]"):
        job_id = card.get("data-occludable-job-id")
        if not job_id:
            continue

        title_el = card.select_one("a.job-card-container__link")
        # aria-label holds the clean title text; get_text() picks up both the
        # visible <strong> span and a duplicate .visually-hidden a11y span.
        title = title_el.get("aria-label", "").strip() if title_el else ""
        if not title:
            continue
        title = re.sub(r"\s+with verification$", "", title)

        company_el = card.select_one(".artdeco-entity-lockup__subtitle")
        company = company_el.get_text(strip=True) if company_el else ""

        caption_items = card.select(".artdeco-entity-lockup__caption li")
        location = caption_items[0].get_text(strip=True) if caption_items else ""

        # Only shows for genuinely fresh, not-yet-"Viewed" postings — most
        # cards within a short f_TPR window will have it, older or
        # already-viewed ones legitimately won't.
        posted_time = ""
        for footer_item in card.select(".job-card-container__footer-item"):
            match = _POSTED_TIME_RE.search(footer_item.get_text(" ", strip=True))
            if match:
                posted_time = match.group(0)
                break

        results.append(
            {
                "job_id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "posted_time": posted_time,
                "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
                "scraped_at": scraped_at,
            }
        )

    return results
