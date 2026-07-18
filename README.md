# clinical_dates

Extraction and normalization of dates from Russian clinical text.

Pure Python, zero dependencies. Designed for medical NLP pipelines that process
Russian-language clinical notes, consilium reports, and patient records.

## Features

- **Multiple date formats:**
  - ISO: `2024-01-15`
  - DD.MM.YYYY: `15.01.2024` (also `/`, `-` separators)
  - DD.MM.YY: `01.08.23` → `2023-08-01` (2-digit year, smart 19XX/20XX threshold)
  - MM.YYYY: `01.2024`
  - Month name + year: `январь 2024`, `15 января 2024`, `в мае 2026`
  - Bare year: `2024`

- **Date ranges:** `с 15.01.2024 по 12.02.2024` — extracts start and end as a pair

- **Position-aware:** every `DateMatch` includes char offsets, enabling proximity-based
  linking (e.g. "find dates near a drug mention")

- **Granularity:** `day`, `month`, or `year` — so `январь 2024` is distinguishable
  from `15.01.2024`

- **Overlap resolution:** when patterns compete for the same text span, the most
  specific match wins (ISO/DMY > MM.YYYY > month+year > bare year)

## Installation

```bash
pip install -e .
```

Or from GitHub:

```bash
pip install git+https://github.com/<user>/clinical_dates.git
```

## Quick start

```python
from clinical_dates import extract_dates, extract_date_ranges

text = """
1-я линия: Карбоплатин + Пеметрексед с 15.01.2024 по 12.02.2024.
Прогрессирование. 2-я линия: Пембролизумаб с 09.06.25, продолжается.
Пациент осмотрен в мае 2026.
"""

# Extract all dates
for d in extract_dates(text):
    print(f"  {d.iso}  ({d.granularity})  ← '{d.label}'  @ pos {d.start}")

# Extract "с ... по ..." ranges
for r in extract_date_ranges(text):
    print(f"  {r.start_iso} → {r.end_iso}")
```

Output:
```
  2024-01-15  (day)  ← '15 января 2024'  @ pos 44
  2024-02-12  (day)  ← '12 февраля 2024'  @ pos 60
  2025-06-09  (day)  ← '09 июня 2025'  @ pos 121
  2026-05-01  (month)  ← 'май 2026'  @ pos 164

  2024-01-15 → 2024-02-12
```

## API

| Function | Returns | Description |
|---|---|---|
| `extract_dates(text)` | `List[DateMatch]` | All dates, sorted by position |
| `extract_date_ranges(text)` | `List[DateRange]` | All `с ... по ...` ranges |
| `parse_date(raw)` | `Optional[str]` | Parse a single date string → ISO |
| `find_dates_near_position(text, pos, window)` | `List[DateMatch]` | Dates within `window` chars of `pos` |
| `find_ranges_near_position(text, pos, window)` | `List[DateRange]` | Ranges within `window` chars of `pos` |

### `DateMatch`

| Field | Type | Description |
|---|---|---|
| `iso` | `str` | Normalized date `YYYY-MM-DD` |
| `granularity` | `str` | `day`, `month`, or `year` |
| `label` | `str` | Human-readable label (e.g. `15 января 2024`) |
| `start` | `int` | Char offset in source text |
| `end` | `int` | Char offset (exclusive) |

### `DateRange`

| Field | Type | Description |
|---|---|---|
| `start_match` | `DateMatch` | Start date |
| `end_match` | `DateMatch` | End date |
| `start` | `int` | Char offset of entire range |
| `end` | `int` | Char offset (exclusive) |

## Use cases

- **Oncology pipelines:** extract therapy line dates, treatment periods, follow-up timelines
- **Clinical NLP:** link lab values to nearest preceding date for timeline construction
- **Medical record parsing:** normalize free-text dates to ISO 8601

## Testing

```bash
pytest tests/ -v
```

## License

MIT
