"""
clinical_dates — shared clinical date extraction package.

Public API:
    from clinical_dates import extract_dates, DateMatch, extract_date_ranges, DateRange

    dates = extract_dates(text)          # all dates, sorted by position
    ranges = extract_date_ranges(text)   # "с ... по ..." ranges
"""
from .core import (
    DateMatch,
    DateRange,
    extract_dates,
    extract_date_ranges,
    parse_date,
    find_dates_near_position,
    find_ranges_near_position,
)

__all__ = [
    "DateMatch",
    "DateRange",
    "extract_dates",
    "extract_date_ranges",
    "parse_date",
    "find_dates_near_position",
    "find_ranges_near_position",
]

__version__ = "0.1.0"
