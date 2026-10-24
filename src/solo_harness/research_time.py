"""Timezone policy for researcher-facing representations.

Database timestamps remain timezone-aware UTC values. This module is only for
display and export representations used by researchers.
"""
from datetime import datetime
from zoneinfo import ZoneInfo


RESEARCH_TIMEZONE_NAME = "Asia/Kolkata"
RESEARCH_TIMEZONE = ZoneInfo(RESEARCH_TIMEZONE_NAME)


def in_research_timezone(value: datetime | None) -> datetime | None:
    return value.astimezone(RESEARCH_TIMEZONE) if value is not None else None
