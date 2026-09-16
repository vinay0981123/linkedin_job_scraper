"""Rule-based keyword matching — plain regex, no AI/ML involved."""

import re

import config

_PATTERNS = [
    (kw, re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE))
    for kw in config.KEYWORDS
]


def matching_keywords(job_title: str) -> list[str]:
    return [kw for kw, pattern in _PATTERNS if pattern.search(job_title)]


def build_search_query() -> str:
    """LinkedIn's keyword box supports boolean OR + quoted phrases, so all
    target titles can be searched in a single query per city."""
    parts = [f'"{kw}"' if " " in kw else kw for kw in config.KEYWORDS]
    return " OR ".join(parts)
