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
JOB_VIEW_BASE = "https://www.linkedin.com/jobs/view/"

_POSTED_TIME_RE = re.compile(r"\b(\d+)\s+(minute|hour|day|week|month)s?\s+ago\b", re.IGNORECASE)

_MINUTES_PER_UNIT = {
    "minute": 1,
    "hour": 60,
    "day": 24 * 60,
    "week": 7 * 24 * 60,
    "month": 30 * 24 * 60,
}


def posted_minutes_ago(posted_time_text: str) -> int | None:
    """Parses "X minutes/hours/days/... ago" into a minute count. Returns
    None when the text is blank or doesn't match — treat that as unknown
    age, not zero, since LinkedIn only shows this badge for some cards."""
    if not posted_time_text:
        return None
    match = _POSTED_TIME_RE.search(posted_time_text)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2).lower()
    return value * _MINUTES_PER_UNIT[unit]


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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    retry=retry_if_exception_type((PlaywrightTimeoutError, PlaywrightError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def fetch_job_details(page, job_url: str) -> tuple[str, str]:
    """Returns (description, posted_time_text) from a job's own detail page.

    description: used to check the stated experience requirement, which
    never appears on the search card. Container id is
    "JobDetails_AboutTheJob_<jobId>", matched by prefix since the numeric
    suffix varies per job.

    posted_time_text: fallback for when the search card showed no time
    badge at all (LinkedIn auto-opens the top result in a preview pane just
    from loading the search page, which marks it "Viewed" and suppresses
    its badge — this can hide the single freshest, most relevant result).
    The detail page's own indicator is the only <strong> tag on the page
    containing "ago" text — every other "X ago" mention is unrelated noise
    from the "similar jobs" sidebar, which uses <span>, not <strong>.
    """
    page.goto(job_url, wait_until="domcontentloaded", timeout=45_000)
    page.wait_for_timeout(1500)

    soup = BeautifulSoup(page.content(), "html.parser")

    container = soup.select_one('div[id^="JobDetails_AboutTheJob_"]')
    description = container.get_text(" ", strip=True) if container else ""

    posted_el = soup.find("strong", string=lambda s: s and "ago" in s.lower())
    posted_time_text = posted_el.get_text(strip=True) if posted_el else ""

    return description, posted_time_text


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
