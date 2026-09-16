"""Extracts a minimum-years-of-experience requirement from free-text job
descriptions via regex — plain pattern matching, no AI/ML involved.

Handles the common ways postings phrase this: "2 to 6 years", "2-6 years",
"3 years", "3+ years", "minimum 3 years of experience", etc. Takes the
first match found in the description text; a posting mentioning multiple
different experience requirements (e.g. per sub-skill) isn't disambiguated
further — that would need actual language understanding, out of scope for
a regex-only matcher.
"""

import re

_RANGE_RE = re.compile(
    r"(\d{1,2})\s*(?:-|–|—|to)\s*(\d{1,2})\+?\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
_PLUS_RE = re.compile(
    r"(\d{1,2})\s*\+\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
_MINIMUM_RE = re.compile(
    r"(?:minimum|min\.?|at least|over)\s*(?:of\s*)?(\d{1,2})\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
_SINGLE_RE = re.compile(
    r"(\d{1,2})\s*(?:years?|yrs?)(?:\s+of)?\s*(?:experience|exp\b)",
    re.IGNORECASE,
)

_PATTERNS = (_RANGE_RE, _PLUS_RE, _MINIMUM_RE, _SINGLE_RE)


def extract_min_years(text: str) -> tuple[int | None, str | None]:
    """Returns (minimum_years_required, matched_snippet) — both None if no
    experience requirement was found in the text."""
    for pattern in _PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1)), match.group(0).strip()
    return None, None


def meets_experience_requirement(text: str, max_years: int) -> tuple[bool, str]:
    """Returns (qualifies, display_text). Qualifies is False only when a
    requirement was actually detected and its minimum exceeds max_years —
    an undetected/unstated requirement never disqualifies a posting."""
    min_years, snippet = extract_min_years(text)
    if min_years is None:
        return True, "Not specified"
    if min_years > max_years:
        return False, snippet
    return True, snippet
