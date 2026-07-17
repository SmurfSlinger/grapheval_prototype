"""Deterministic date-range interval parsing and comparison."""

from __future__ import annotations

import re
from dataclasses import dataclass

MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

YEAR_PATTERN = r"(19\d{2}|20\d{2})"


@dataclass(frozen=True)
class DateInterval:
    start_month: int | None
    start_day: int | None
    end_month: int | None
    end_day: int | None
    year: int | None

    def is_complete(self) -> bool:
        return all(
            value is not None
            for value in (self.start_month, self.start_day, self.end_month, self.end_day, self.year)
        )


def parse_date_interval(text: str) -> DateInterval | None:
    cleaned = " ".join(text.lower().split())
    year_match = re.search(rf"\b{YEAR_PATTERN}\b", cleaned)
    year = int(year_match.group(1)) if year_match else None

    between_full = re.search(
        rf"between\s+([a-z]+)\s+(\d{{1,2}})\s+and\s+([a-z]+)\s+(\d{{1,2}})(?:,\s*{YEAR_PATTERN})?",
        cleaned,
    )
    if between_full:
        sm = MONTHS.get(between_full.group(1))
        em = MONTHS.get(between_full.group(3))
        if sm and em:
            parsed_year = int(between_full.group(5)) if between_full.group(5) else year
            return DateInterval(
                sm,
                int(between_full.group(2)),
                em,
                int(between_full.group(4)),
                parsed_year,
            )

    between = re.search(
        rf"between\s+([a-z]+)\s+(\d{{1,2}})\s+and\s+(\d{{1,2}})(?:,\s*{YEAR_PATTERN})?",
        cleaned,
    )
    if between:
        month = MONTHS.get(between.group(1))
        if month:
            parsed_year = int(between.group(4)) if between.group(4) else year
            return DateInterval(month, int(between.group(2)), month, int(between.group(3)), parsed_year)

    to_full = re.search(
        rf"([a-z]+)\s+(\d{{1,2}})\s+to\s+([a-z]+)\s+(\d{{1,2}})(?:,\s*{YEAR_PATTERN})?",
        cleaned,
    )
    if to_full:
        sm = MONTHS.get(to_full.group(1))
        em = MONTHS.get(to_full.group(3))
        if sm and em:
            parsed_year = int(to_full.group(5)) if to_full.group(5) else year
            return DateInterval(sm, int(to_full.group(2)), em, int(to_full.group(4)), parsed_year)

    through = re.search(
        rf"([a-z]+)\s+(\d{{1,2}})\s+through\s+([a-z]+)\s+(\d{{1,2}})(?:,\s*{YEAR_PATTERN})?",
        cleaned,
    )
    if through:
        sm = MONTHS.get(through.group(1))
        em = MONTHS.get(through.group(3))
        if sm and em:
            parsed_year = int(through.group(5)) if through.group(5) else year
            return DateInterval(
                sm,
                int(through.group(2)),
                em,
                int(through.group(4)),
                parsed_year,
            )

    to_shared = re.search(
        rf"([a-z]+)\s+(\d{{1,2}})\s+to\s+(\d{{1,2}})(?:,\s*{YEAR_PATTERN})?",
        cleaned,
    )
    if to_shared:
        month = MONTHS.get(to_shared.group(1))
        if month:
            parsed_year = int(to_shared.group(4)) if to_shared.group(4) else year
            return DateInterval(
                month,
                int(to_shared.group(2)),
                month,
                int(to_shared.group(3)),
                parsed_year,
            )

    and_shared = re.search(
        rf"([a-z]+)\s+(\d{{1,2}})\s+and\s+(\d{{1,2}})(?:,\s*{YEAR_PATTERN})?",
        cleaned,
    )
    if and_shared:
        month = MONTHS.get(and_shared.group(1))
        if month:
            parsed_year = int(and_shared.group(4)) if and_shared.group(4) else year
            return DateInterval(
                month,
                int(and_shared.group(2)),
                month,
                int(and_shared.group(3)),
                parsed_year,
            )

    hyphen = re.search(
        rf"([a-z]+)\s+(\d{{1,2}})\s*[-–—]\s*(\d{{1,2}})(?:,\s*{YEAR_PATTERN})?",
        cleaned,
    )
    if hyphen:
        month = MONTHS.get(hyphen.group(1))
        if month:
            parsed_year = int(hyphen.group(4)) if hyphen.group(4) else year
            return DateInterval(
                month,
                int(hyphen.group(2)),
                month,
                int(hyphen.group(3)),
                parsed_year,
            )

    cross_month = re.search(
        rf"([a-z]+)\s+(\d{{1,2}})\s*[-–—]\s*([a-z]+)\s+(\d{{1,2}})(?:,\s*{YEAR_PATTERN})?",
        cleaned,
    )
    if cross_month:
        sm = MONTHS.get(cross_month.group(1))
        em = MONTHS.get(cross_month.group(3))
        if sm and em:
            parsed_year = int(cross_month.group(5)) if cross_month.group(5) else year
            return DateInterval(
                sm,
                int(cross_month.group(2)),
                em,
                int(cross_month.group(4)),
                parsed_year,
            )

    return None


def date_intervals_equivalent(left: str, right: str) -> bool:
    left_interval = parse_date_interval(left)
    right_interval = parse_date_interval(right)
    if left_interval is None or right_interval is None:
        return False
    if not left_interval.is_complete() or not right_interval.is_complete():
        return False
    return left_interval == right_interval
