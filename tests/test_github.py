import unittest
from datetime import date, timedelta
from pathlib import Path

from vitrina.github import Day, contributions_url, github_view, parse_contributions

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE = (FIXTURES / "github_contributions.html").read_text(encoding="utf-8")
REAL = (FIXTURES / "github_contributions_real.html").read_text(encoding="utf-8")
TODAY = date(2026, 11, 12)


def empty_days(first, last):
    n = (last - first).days + 1
    return [Day(first + timedelta(days=i), 0, 0) for i in range(n)]


class ParseTest(unittest.TestCase):
    def test_parses_days_sorted_with_counts(self):
        days = parse_contributions(FIXTURE)
        self.assertEqual(len(days), 12)
        self.assertEqual(days[0], Day(date(2026, 11, 1), 2, 4))
        self.assertEqual(days[4], Day(date(2026, 11, 5), 4, 1024))
        self.assertEqual(days[-1], Day(date(2026, 11, 12), 0, 0))

    def test_unknown_html_raises(self):
        with self.assertRaises(ValueError):
            parse_contributions("<html>rate limited</html>")

    def test_real_page(self):
        days = parse_contributions(REAL)
        self.assertTrue(365 <= len(days) <= 371, len(days))
        self.assertTrue(all(0 <= d.level <= 4 for d in days))
        self.assertTrue(all(d.count == 0 for d in days if d.level == 0))
        self.assertEqual(days, sorted(days, key=lambda d: d.date))

    def test_url_is_quoted(self):
        self.assertEqual(contributions_url("nicob201"), "https://github.com/users/nicob201/contributions")
        self.assertEqual(contributions_url("a b"), "https://github.com/users/a%20b/contributions")


class ViewTest(unittest.TestCase):
    def test_view_from_fixture(self):
        v = github_view(parse_contributions(FIXTURE), TODAY)
        self.assertEqual((v["total"], v["streak"], v["today"]), (1043, 4, 0))
        self.assertEqual(v["weeks"], [[2, 0, 1, 0, 4, 1, 0], [1, 3, 1, 1, 0]])
        self.assertEqual(v["months"], [{"week": 0, "month": 11}])

    def test_streak_includes_today_when_today_has_contributions(self):
        v = github_view(parse_contributions(FIXTURE), date(2026, 11, 11))
        self.assertEqual((v["streak"], v["today"]), (4, 2))

    def test_missing_day_breaks_the_streak(self):
        days = [d for d in parse_contributions(FIXTURE) if d.date != date(2026, 11, 9)]
        self.assertEqual(github_view(days, TODAY)["streak"], 2)

    def test_days_after_today_are_ignored(self):
        days = parse_contributions(FIXTURE) + [Day(date(2026, 11, 13), 4, 9)]
        v = github_view(days, TODAY)
        self.assertEqual((v["total"], v["today"], v["streak"]), (1043, 0, 4))

    def test_first_week_is_padded_when_it_starts_midweek(self):
        days = [d for d in parse_contributions(FIXTURE) if d.date >= date(2026, 11, 4)]
        v = github_view(days, TODAY)
        self.assertEqual(v["weeks"][0], [None, None, None, 0, 4, 1, 0])

    def test_month_labels(self):
        v = github_view(empty_days(date(2026, 9, 27), TODAY), TODAY)
        self.assertEqual(v["months"], [{"week": 1, "month": 10}, {"week": 5, "month": 11}])

    def test_first_month_label_kept_when_next_is_far(self):
        v = github_view(empty_days(date(2026, 9, 6), TODAY), TODAY)
        self.assertEqual(v["months"][0], {"week": 0, "month": 9})


if __name__ == "__main__":
    unittest.main()
