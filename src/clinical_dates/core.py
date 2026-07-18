"""
Core date extraction for clinical text (Russian + ISO).

Supports:
- ISO:            2026-05-20
- DD.MM.YYYY:     20.05.2026, 06.06.2024 (also /, -)
- DD.MM.YY:       01.08.23 → 2023-08-01 (2-digit year, assumes 20xx)
- MM.YYYY:        05.2026, 06/2024
- Month + year:   "июнь 2024", "в июне 2024", "мае 2026"
- Year:           2024, 2025
- "с ... по ...": date ranges with start/end

Each date is returned as DateMatch with normalized ISO date,
granularity (day/month/year), human-readable label, and text position.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


# ── Month dictionaries ────────────────────────────────────────────────

_MONTHS = {
    "янв": (1, "январь"), "фев": (2, "февраль"), "мар": (3, "март"),
    "апр": (4, "апрель"), "ма": (5, "май"), "июн": (6, "июнь"),
    "июл": (7, "июль"), "авг": (8, "август"), "сен": (9, "сентябрь"),
    "окт": (10, "октябрь"), "ноя": (11, "ноябрь"), "дек": (12, "декабрь"),
}

_MONTH_NAMES_GENITIVE = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


# ── Data classes ──────────────────────────────────────────────────────

@dataclass
class DateMatch:
    """A single extracted date with metadata."""
    iso: str                 # normalized date YYYY-MM-DD
    granularity: str         # day | month | year
    label: str               # human-readable label
    start: int               # char offset in source text
    end: int                 # char offset (exclusive)

    @property
    def sort_key(self) -> str:
        return self.iso


@dataclass
class DateRange:
    """A "с ... по ..." date range."""
    start_match: DateMatch
    end_match: DateMatch
    start: int               # char offset of the whole range
    end: int                 # char offset (exclusive)

    @property
    def start_iso(self) -> str:
        return self.start_match.iso

    @property
    def end_iso(self) -> str:
        return self.end_match.iso


# ── Helpers ───────────────────────────────────────────────────────────

def _label_for(year: int, month: Optional[int], day: Optional[int]) -> str:
    if day and month:
        return f"{day:02d} {_MONTH_NAMES_GENITIVE[month]} {year}"
    if month:
        return f"{_MONTH_NAMES_GENITIVE[month]} {year}".replace("мая", "май")
    return str(year)


def _norm(year: int, month: Optional[int], day: Optional[int]) -> Tuple[str, str]:
    m = month or 1
    d = day or 1
    iso = f"{year:04d}-{m:02d}-{d:02d}"
    gran = "day" if day else ("month" if month else "year")
    return iso, gran


# ── Regex patterns (order = priority) ─────────────────────────────────

_RE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_RE_DMY = re.compile(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\b")
_RE_DMY_2Y = re.compile(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2})\b(?!\d)")
_RE_MY = re.compile(r"\b(\d{1,2})[.\-/](\d{4})\b")
_RE_MONTH_NAME = re.compile(
    r"\b(янв\w*|фев\w*|март\w*|мар\b|апр\w*|ма[йяе]\b|июн\w*|июл\w*|авг\w*|"
    r"сен\w*|окт\w*|ноя\w*|дек\w*)\s+(\d{4})\b",
    re.IGNORECASE,
)
_RE_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")

# "с ... по ..." date range — captures two dates in DD.MM.YYYY or DD.MM.YY format
_RE_RANGE_DMY = re.compile(
    r"(?i)\bс\s+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})\s+по\s+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})\b"
)
# "с ... по ..." with month names: "с 15 января 2024 по 12 февраля 2024"
_RE_RANGE_MONTH = re.compile(
    r"(?i)\bс\s+(\d{1,2}\s+\w+\s+\d{4})\s+по\s+(\d{1,2}\s+\w+\s+\d{4})\b"
)
# "с ... по ..." with ISO dates
_RE_RANGE_ISO = re.compile(
    r"(?i)\bс\s+(\d{4}-\d{2}-\d{2})\s+по\s+(\d{4}-\d{2}-\d{2})\b"
)


def _month_from_word(word: str) -> Optional[int]:
    w = word.lower()
    # order matters: "ма" (май) — after longer stems
    for stem in ("янв", "фев", "март", "мар", "апр", "июн", "июл", "авг",
                 "сен", "окт", "ноя", "дек", "ма"):
        if w.startswith(stem):
            return _MONTHS[stem if stem != "март" else "мар"][0]
    return None


# ── Public API ────────────────────────────────────────────────────────

def parse_date(raw: str) -> Optional[str]:
    """Parse a single date string to ISO format YYYY-MM-DD.

    Handles DD.MM.YYYY, DD.MM.YY, YYYY-MM-DD, "январь 2024", etc.
    Returns None if parsing fails.
    """
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    if not raw:
        return None

    # ISO format
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            return f"{y:04d}-{mo:02d}-{d:02d}"

    # DD.MM.YYYY
    m = re.match(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})", raw)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            return f"{y:04d}-{mo:02d}-{d:02d}"

    # DD.MM.YY (2-digit year → 19XX/20XX based on threshold)
    m = re.match(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2})", raw)
    if m:
        d, mo, y2 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            year = 2000 + y2 if y2 < 50 else 1900 + y2
            return f"{year:04d}-{mo:02d}-{d:02d}"

    # Month name + year: "январь 2024", "15 января 2024"
    m = re.match(r"(?i)(\d{1,2}\s+)?(янв\w*|фев\w*|март\w*|мар\b|апр\w*|ма[йяе]\b|июн\w*|июл\w*|авг\w*|сен\w*|окт\w*|ноя\w*|дек\w*)\s+(\d{4})", raw)
    if m:
        day = int(m.group(1)) if m.group(1) else None
        month = _month_from_word(m.group(2))
        year = int(m.group(3))
        if month and 1 <= month <= 12:
            if day and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
            return f"{year:04d}-{month:02d}-01"

    # MM.YYYY
    m = re.match(r"(\d{1,2})[.\-/](\d{4})", raw)
    if m:
        mo, y = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return f"{y:04d}-{mo:02d}-01"

    return None


def extract_dates(text: str) -> List[DateMatch]:
    """Extract all dates from text, sorted by position.

    Overlapping matches are resolved by priority: ISO/DMY > DMY-2Y > MY >
    month+year > bare year (more specific wins).
    """
    if not text:
        return []

    claimed: List[Tuple[int, int]] = []

    def overlaps(s: int, e: int) -> bool:
        return any(not (e <= cs or s >= ce) for cs, ce in claimed)

    matches: List[DateMatch] = []

    def add(s: int, e: int, year: int, month: Optional[int], day: Optional[int]):
        if not (1900 <= year <= 2100):
            return
        if month and not (1 <= month <= 12):
            return
        if day and not (1 <= day <= 31):
            return
        if overlaps(s, e):
            return
        iso, gran = _norm(year, month, day)
        matches.append(DateMatch(iso, gran, _label_for(year, month, day), s, e))
        claimed.append((s, e))

    # ISO: YYYY-MM-DD
    for mt in _RE_ISO.finditer(text):
        add(mt.start(), mt.end(), int(mt.group(1)), int(mt.group(2)), int(mt.group(3)))

    # DD.MM.YYYY (4-digit year)
    for mt in _RE_DMY.finditer(text):
        add(mt.start(), mt.end(), int(mt.group(3)), int(mt.group(2)), int(mt.group(1)))

    # DD.MM.YY (2-digit year → 20YY)
    for mt in _RE_DMY_2Y.finditer(text):
        y2 = int(mt.group(3))
        year = 2000 + y2 if y2 < 50 else 1900 + y2
        add(mt.start(), mt.end(), year, int(mt.group(2)), int(mt.group(1)))

    # MM.YYYY
    for mt in _RE_MY.finditer(text):
        add(mt.start(), mt.end(), int(mt.group(2)), int(mt.group(1)), None)

    # Month name + year
    for mt in _RE_MONTH_NAME.finditer(text):
        month = _month_from_word(mt.group(1))
        if month:
            add(mt.start(), mt.end(), int(mt.group(2)), month, None)

    # Bare year (lowest priority)
    for mt in _RE_YEAR.finditer(text):
        add(mt.start(), mt.end(), int(mt.group(1)), None, None)

    matches.sort(key=lambda d: d.start)
    return matches


def extract_date_ranges(text: str) -> List[DateRange]:
    """Extract "с ... по ..." date ranges from text.

    Returns DateRange objects with start/end DateMatch, sorted by position.
    """
    if not text:
        return []

    ranges: List[DateRange] = []

    # Pattern 1: "с DD.MM.YYYY по DD.MM.YYYY" (or DD.MM.YY)
    for mt in _RE_RANGE_DMY.finditer(text):
        start_raw = mt.group(1)
        end_raw = mt.group(2)
        start_iso = parse_date(start_raw)
        end_iso = parse_date(end_raw)
        if start_iso and end_iso:
            s_start = mt.start(1)
            s_end = mt.end(1)
            e_start = mt.start(2)
            e_end = mt.end(2)
            ranges.append(DateRange(
                start_match=DateMatch(start_iso, "day", start_raw, s_start, s_end),
                end_match=DateMatch(end_iso, "day", end_raw, e_start, e_end),
                start=mt.start(),
                end=mt.end(),
            ))

    # Pattern 2: "с DD <month> YYYY по DD <month> YYYY"
    for mt in _RE_RANGE_MONTH.finditer(text):
        start_raw = mt.group(1)
        end_raw = mt.group(2)
        start_iso = parse_date(start_raw)
        end_iso = parse_date(end_raw)
        if start_iso and end_iso:
            ranges.append(DateRange(
                start_match=DateMatch(start_iso, "day", start_raw, mt.start(1), mt.end(1)),
                end_match=DateMatch(end_iso, "day", end_raw, mt.start(2), mt.end(2)),
                start=mt.start(),
                end=mt.end(),
            ))

    # Pattern 3: "с YYYY-MM-DD по YYYY-MM-DD"
    for mt in _RE_RANGE_ISO.finditer(text):
        start_iso = mt.group(1)
        end_iso = mt.group(2)
        ranges.append(DateRange(
            start_match=DateMatch(start_iso, "day", start_iso, mt.start(1), mt.end(1)),
            end_match=DateMatch(end_iso, "day", end_iso, mt.start(2), mt.end(2)),
            start=mt.start(),
            end=mt.end(),
        ))

    ranges.sort(key=lambda r: r.start)
    return ranges


def find_dates_near_position(
    text: str,
    position: int,
    window: int = 200,
    min_year: int = 2000,
) -> List[DateMatch]:
    """Find all dates within `window` chars of `position`, filtered by min_year.

    Useful for finding dates near a drug mention or therapy keyword.
    """
    all_dates = extract_dates(text)
    nearby = []
    for dm in all_dates:
        if abs(dm.start - position) > window:
            continue
        try:
            year = int(dm.iso[:4])
            if year < min_year:
                continue
        except (ValueError, IndexError):
            continue
        nearby.append(dm)
    return nearby


def find_ranges_near_position(
    text: str,
    position: int,
    window: int = 300,
) -> List[DateRange]:
    """Find "с ... по ..." date ranges within `window` chars of `position`."""
    all_ranges = extract_date_ranges(text)
    nearby = []
    for dr in all_ranges:
        if abs(dr.start - position) > window:
            continue
        nearby.append(dr)
    return nearby
