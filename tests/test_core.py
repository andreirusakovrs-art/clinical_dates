"""Tests for clinical_dates package."""
import pytest
from clinical_dates import (
    extract_dates,
    extract_date_ranges,
    parse_date,
    find_dates_near_position,
    find_ranges_near_position,
    DateMatch,
    DateRange,
)


class TestParseDate:
    def test_iso(self):
        assert parse_date("2024-01-15") == "2024-01-15"

    def test_dmy_4digit(self):
        assert parse_date("15.01.2024") == "2024-01-15"

    def test_dmy_2digit(self):
        assert parse_date("01.08.23") == "2023-08-01"

    def test_dmy_2digit_old(self):
        # 50+ → 19XX
        assert parse_date("01.01.99") == "1999-01-01"

    def test_dmy_slash(self):
        assert parse_date("15/01/2024") == "2024-01-15"

    def test_dmy_dash(self):
        assert parse_date("15-01-2024") == "2024-01-15"

    def test_month_name(self):
        assert parse_date("январь 2024") == "2024-01-01"

    def test_month_name_day(self):
        assert parse_date("15 января 2024") == "2024-01-15"

    def test_my(self):
        assert parse_date("01.2024") == "2024-01-01"

    def test_invalid(self):
        assert parse_date("not a date") is None

    def test_empty(self):
        assert parse_date("") is None
        assert parse_date(None) is None


class TestExtractDates:
    def test_mixed_formats(self):
        text = "06.06.2024 ... май 2026 ... 2025 ... 2026-05-20 ... 05.2026"
        dates = extract_dates(text)
        isos = {d.iso for d in dates}
        assert "2024-06-06" in isos
        assert "2026-05-01" in isos  # "май 2026"
        assert "2026-05-20" in isos  # ISO
        assert any(d.granularity == "year" for d in dates)

    def test_2digit_year(self):
        text = "Терапия с 01.08.23 по 15.12.23"
        dates = extract_dates(text)
        isos = {d.iso for d in dates}
        assert "2023-08-01" in isos
        assert "2023-12-15" in isos

    def test_sorted_by_position(self):
        text = "2024-01-01 ... 2023-06-15 ... 2025-03-20"
        dates = extract_dates(text)
        positions = [d.start for d in dates]
        assert positions == sorted(positions)

    def test_overlap_resolution(self):
        text = "05.2026"
        dates = extract_dates(text)
        # Should match as MM.YYYY, not as bare year 2026
        assert len(dates) == 1
        assert dates[0].granularity == "month"

    def test_empty(self):
        assert extract_dates("") == []
        assert extract_dates(None) == []


class TestExtractDateRanges:
    def test_basic_range(self):
        text = "Лечение с 15.01.2024 по 12.02.2024"
        ranges = extract_date_ranges(text)
        assert len(ranges) == 1
        assert ranges[0].start_iso == "2024-01-15"
        assert ranges[0].end_iso == "2024-02-12"

    def test_2digit_range(self):
        text = "Терапия с 01.08.23 по 15.12.23"
        ranges = extract_date_ranges(text)
        assert len(ranges) == 1
        assert ranges[0].start_iso == "2023-08-01"
        assert ranges[0].end_iso == "2023-12-15"

    def test_month_name_range(self):
        text = "с 15 января 2024 по 12 февраля 2024"
        ranges = extract_date_ranges(text)
        assert len(ranges) == 1
        assert ranges[0].start_iso == "2024-01-15"
        assert ranges[0].end_iso == "2024-02-12"

    def test_iso_range(self):
        text = "с 2024-01-15 по 2024-02-12"
        ranges = extract_date_ranges(text)
        assert len(ranges) == 1
        assert ranges[0].start_iso == "2024-01-15"
        assert ranges[0].end_iso == "2024-02-12"

    def test_multiple_ranges(self):
        text = "1-я линия с 15.01.2024 по 12.02.2024. 2-я линия с 09.06.2025 по 01.08.25"
        ranges = extract_date_ranges(text)
        assert len(ranges) == 2
        assert ranges[0].start_iso == "2024-01-15"
        assert ranges[1].start_iso == "2025-06-09"

    def test_no_range(self):
        text = "Терапия начата 15.01.2024"
        ranges = extract_date_ranges(text)
        assert len(ranges) == 0


class TestFindDatesNearPosition:
    def test_basic(self):
        text = "Пациент осмотрен 15.01.2024. Назначена терапия. 20.01.2024 начат 1-й цикл."
        dates = extract_dates(text)
        # Find position of "1-й цикл"
        pos = text.index("1-й цикл")
        nearby = find_dates_near_position(text, pos, window=50)
        isos = {d.iso for d in nearby}
        assert "2024-01-20" in isos

    def test_filters_old_years(self):
        text = "Родился в 1965. Терапия 15.01.2024"
        pos = text.index("Терапия")
        nearby = find_dates_near_position(text, pos, window=50, min_year=2000)
        isos = {d.iso for d in nearby}
        assert "1965-01-01" not in isos
        assert "2024-01-15" in isos


class TestFindRangesNearPosition:
    def test_basic(self):
        text = "1-я линия: Карбоплатин + Пеметрексед с 15.01.2024 по 12.02.2024. Прогрессирование."
        pos = text.index("Карбоплатин")
        ranges = find_ranges_near_position(text, pos, window=100)
        assert len(ranges) >= 1
        assert ranges[0].start_iso == "2024-01-15"
        assert ranges[0].end_iso == "2024-02-12"
