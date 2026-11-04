"""IVAC appointment preparation guidance derived from the published FAQ."""

from datetime import date
from typing import Optional

MAX_APPLICANTS = 4
MAX_WEBFILE_AGE_DAYS = 30
OFFICIAL_FAQ_URL = "https://www.ivacbd.com/faq/appointment-management-system"


def webfile_age_days(webfile_date: date, today: Optional[date] = None) -> int:
    """Return age in calendar days; future document dates return a negative value."""
    return ((today or date.today()) - webfile_date).days


def webfile_age_status(webfile_date: date, today: Optional[date] = None) -> tuple[bool, str]:
    """Assess the date a user read from their original Webfile; no date is inferred."""
    age = webfile_age_days(webfile_date, today)
    if age < 0:
        return False, "Date is in the future; check it against the original Webfile."
    if age > MAX_WEBFILE_AGE_DAYS:
        return False, f"Webfile is {age} days old; IVAC FAQ says it must be no older than 30 days."
    return True, f"Webfile date is {age} days old (within the 30-day limit)."
