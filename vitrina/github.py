from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from html.parser import HTMLParser
from urllib.parse import quote


@dataclass(frozen=True)
class Day:
    date: date
    level: int  # 0-4, as GitHub shades the cell
    count: int


def contributions_url(user: str) -> str:
    return f"https://github.com/users/{quote(user)}/contributions"


class _CalendarParser(HTMLParser):
    """Cells come row by row (one row per weekday); counts live in separate tool-tips."""

    def __init__(self) -> None:
        super().__init__()
        self.cells: dict[str, tuple[date, int]] = {}
        self.tips: dict[str, str] = {}
        self._tip: str | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "td" and "ContributionCalendar-day" in (a.get("class") or "").split():
            if a.get("data-date") and a.get("id"):
                self.cells[a["id"]] = (date.fromisoformat(a["data-date"]), int(a.get("data-level") or 0))
        elif tag == "tool-tip" and a.get("for"):
            self._tip = a["for"]
            self.tips[self._tip] = ""

    def handle_data(self, data):
        if self._tip:
            self.tips[self._tip] += data

    def handle_endtag(self, tag):
        if tag == "tool-tip":
            self._tip = None


def parse_contributions(html: str) -> list[Day]:
    parser = _CalendarParser()
    parser.feed(html)
    if not parser.cells:
        raise ValueError("no contribution days found (did GitHub change the page?)")
    days = []
    for cell_id, (day, level) in parser.cells.items():
        m = re.match(r"\s*([\d,]+)", parser.tips.get(cell_id, ""))  # "No contributions…" → 0
        days.append(Day(day, level, int(m.group(1).replace(",", "")) if m else 0))
    return sorted(days, key=lambda d: d.date)


def github_view(days: list[Day], today: date) -> dict:
    # GitHub can already show "tomorrow" late at night; the PC's date is the truth.
    days = [d for d in days if d.date <= today]
    counts = {d.date: d.count for d in days}

    streak = 0
    day = today if counts.get(today, 0) else today - timedelta(days=1)  # today isn't over yet
    while counts.get(day, 0) > 0:
        streak += 1
        day -= timedelta(days=1)

    weeks: list[list[int | None]] = []
    first_of_week: dict[int, date] = {}
    if days:
        start = days[0].date - timedelta(days=(days[0].date.weekday() + 1) % 7)  # Sunday
        for d in days:
            w, slot = divmod((d.date - start).days, 7)
            while len(weeks) <= w:
                weeks.append([])
            weeks[w].extend([None] * (slot - len(weeks[w])))
            weeks[w].append(d.level)
            first_of_week.setdefault(w, d.date)

    months: list[dict] = []
    for w in sorted(first_of_week):
        month = first_of_week[w].month
        if not months or months[-1]["month"] != month:
            months.append({"week": w, "month": month})
    if len(months) > 1 and months[0]["week"] == 0 and months[1]["week"] <= 2:
        months.pop(0)  # a sliver of a month at the left edge would crowd the next label

    return {
        "total": sum(counts.values()),
        "streak": streak,
        "today": counts.get(today, 0),
        "weeks": weeks,
        "months": months,
    }
