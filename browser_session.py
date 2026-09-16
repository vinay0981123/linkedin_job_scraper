"""Persistent, logged-in browser session.

First run: a window opens, you log in to LinkedIn by hand (this also covers
any 2FA/captcha challenge). Cookies and storage are saved into
BROWSER_PROFILE_DIR, so every later run reuses that session without
re-entering credentials or re-triggering LinkedIn's login flow.

Stealth patches (playwright-stealth) are applied to the context so the
automated browser doesn't expose the usual JS-level automation fingerprints
(navigator.webdriver, etc.) — relevant since this session stays logged in
and runs for long, unattended stretches.
"""

import logging

from playwright.sync_api import BrowserContext, sync_playwright
from playwright_stealth import Stealth

import config

logger = logging.getLogger(__name__)

FEED_URL = "https://www.linkedin.com/feed/"
SESSION_COOKIE_NAME = "li_at"


def _has_session_cookie(context: BrowserContext) -> bool:
    """Ground-truth login check: does LinkedIn's actual session cookie
    exist? This is safer than checking page URLs — a "Continue with
    Google" flow passes through intermediate URLs that match neither
    /login nor /checkpoint while the LinkedIn session still isn't live,
    which previously produced a false "logged in" positive."""
    cookies = context.cookies(["https://www.linkedin.com"])
    return any(c["name"] == SESSION_COOKIE_NAME for c in cookies)


def _wait_for_manual_login(timeout_seconds: int, poll_interval: int, context: BrowserContext) -> bool:
    elapsed = 0
    while elapsed < timeout_seconds:
        if _has_session_cookie(context):
            return True
        context.pages[0].wait_for_timeout(poll_interval * 1000)
        elapsed += poll_interval
    return _has_session_cookie(context)


def open_context() -> tuple[BrowserContext, object]:
    """Returns (context, playwright_instance). Caller must stop() the second."""
    playwright = sync_playwright().start()
    config.BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(config.BROWSER_PROFILE_DIR),
        headless=config.HEADLESS,
        args=(
            [
                "--disable-blink-features=AutomationControlled",
                # Needed when running as root (e.g. in a container) — Chromium
                # refuses its own sandbox in that case otherwise. Harmless
                # outside Docker too; a container already isolates the process.
                "--no-sandbox",
                # /dev/shm is often too small in containers by default,
                # which otherwise crashes Chromium under real page load.
                "--disable-dev-shm-usage",
            ]
            + ([] if config.HEADLESS else ["--start-minimized"])
        ),
        viewport={"width": 1280, "height": 800},
    )
    # navigator_platform_override matches this machine's real Linux UA —
    # the library's own default ("Win32") paired with a Linux user agent is
    # a cross-signal mismatch a real browser would never produce, which is
    # a stronger tell than not spoofing platform at all.
    Stealth(navigator_platform_override="Linux x86_64").apply_stealth_sync(context)

    if not _has_session_cookie(context):
        if config.HEADLESS:
            context.close()
            playwright.stop()
            raise RuntimeError(
                "Not logged in and running headless — there's no visible window for you "
                "to log into. Set HEADLESS = False in config.py, run once to log in, "
                "then switch back to headless."
            )

        logger.info(
            "Not logged in to LinkedIn yet. A browser window has opened — "
            "please log in manually (complete any 2FA/verification steps too). "
            "Waiting up to 5 minutes for you to finish — no need to touch the terminal."
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(FEED_URL)

        if not _wait_for_manual_login(300, 3, context):
            context.close()
            playwright.stop()
            raise RuntimeError(
                "Still not logged in after 5 minutes — aborting. Re-run the script and try again."
            )

        # Chromium batches cookie writes to its on-disk SQLite store (a
        # ~30s commit interval) rather than flushing immediately. Closing
        # the browser right after login (e.g. Ctrl+C to move on to
        # resolve_geo_ids.py) can lose the just-set session cookie if we
        # don't wait it out first — confirmed by testing: an immediate
        # close reliably produced a profile that required logging in again.
        logger.info("Login detected — saving session to disk, please wait...")
        context.pages[0].wait_for_timeout(35_000)

    logger.info("LinkedIn session ready.")
    return context, playwright
