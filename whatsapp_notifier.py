"""Sends a WhatsApp notification via CallMeBot's free personal-use API
(https://www.callmebot.com/blog/free-api-whatsapp-messages/) when new
matching jobs are found. Best-effort: a failure here never affects the
Excel/Sheets writes or the main polling loop.
"""

import logging

import requests
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

import config

logger = logging.getLogger(__name__)

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"
MAX_JOBS_LISTED = 10


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=15),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _send(text: str) -> None:
    response = requests.get(
        CALLMEBOT_URL,
        params={"phone": config.CALLMEBOT_PHONE, "text": text, "apikey": config.CALLMEBOT_APIKEY},
        timeout=15,
    )
    response.raise_for_status()


def _build_message(jobs: list[dict]) -> str:
    lines = [f"{len(jobs)} new LinkedIn job match(es):"]
    for job in jobs[:MAX_JOBS_LISTED]:
        lines.append(f"- {job['title']} @ {job['company']} ({job['location']})\n  {job['url']}")
    remaining = len(jobs) - MAX_JOBS_LISTED
    if remaining > 0:
        lines.append(f"...and {remaining} more — check the sheet/Excel file.")
    return "\n".join(lines)


def notify_new_jobs(jobs: list[dict]) -> None:
    if not jobs or not config.WHATSAPP_ENABLED:
        return

    try:
        _send(_build_message(jobs))
    except Exception:
        logger.exception("Failed to send WhatsApp notification")
