"""Confirms a scraped job's displayed location is actually relevant to one
of the target cities, or is remote. LinkedIn's own location/distance search
filter can be loose (returns jobs outside the searched area), so this is a
second, local check before anything gets written — cast a wide net in the
search URL (see config.SEARCH_DISTANCE_MILES), enforce relevance here.
"""

_LOCATION_KEYWORDS = ["noida", "gurugram", "gurgaon", "delhi", "ncr"]


def is_relevant_location(location_text: str) -> bool:
    if not location_text:
        return False
    lower = location_text.lower()
    if "remote" in lower:
        return True
    return any(keyword in lower for keyword in _LOCATION_KEYWORDS)
