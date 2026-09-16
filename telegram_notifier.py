"""Sends one Telegram notification per new matching job via the official
Bot API (https://core.telegram.org/bots/api#sendmessage) — never bundled,
so every message is exactly one job, never a repeat (dedup_store already
guarantees each job_id only ever reaches here once). Best-effort: a failure
here never affects the Excel/Sheets writes or the main polling loop.
"""

import logging

import requests
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

import config

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=15),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _send(text: str) -> None:
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    response.raise_for_status()


def _build_message(job: dict) -> str:
    return (
        f"New job match: {job['title']}\n"
        f"Company: {job['company']}\n"
        f"Location: {job['location']}\n"
        f"Posted: {job['posted_time']}\n"
        f"Matched Keyword(s): {job['matched_keywords']}\n"
        f"Experience Required: {job['expected_experience']}\n"
        f"Scraped At (UTC): {job['scraped_at']}\n"
        f"{job['url']}"
    )


def notify_new_jobs(jobs: list[dict]) -> None:
    if not jobs or not config.TELEGRAM_ENABLED:
        return

    for job in jobs:
        try:
            _send(_build_message(job))
        except Exception:
            logger.exception("Failed to send Telegram notification for %s", job.get("url"))
