import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from vitrina.claude import USAGE_URL, claude_view, parse_usage, read_token, usage_headers

FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures" / "claude_usage.json").read_text())
NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
CREDS = '{"claudeAiOauth": {"accessToken": "tok", "refreshToken": "r", "expiresAt": 1}}'


class FakeRun:
    def __init__(self, returncode=0, stdout=""):
        self.calls = []
        self.returncode, self.stdout = returncode, stdout

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        return subprocess.CompletedProcess(cmd, self.returncode, self.stdout, "")


class UsageTest(unittest.TestCase):
    def test_view_before_reset(self):
        v = claude_view(parse_usage(FIXTURE), NOW)
        self.assertEqual(v["session"], {"pct": 42, "resets_at": "2026-11-12T14:13:00.123456+00:00"})
        self.assertEqual(v["week"], {"pct": 67, "resets_at": "2026-11-15T12:00:00+00:00", "elapsed_pct": 57})

    def test_session_after_reset_is_zero(self):
        v = claude_view(parse_usage(FIXTURE), NOW.replace(hour=15))
        self.assertEqual(v["session"], {"pct": 0, "resets_at": None})

    def test_week_after_reset_is_zero(self):
        v = claude_view(parse_usage(FIXTURE), datetime(2026, 11, 16, tzinfo=timezone.utc))
        self.assertEqual(v["week"], {"pct": 0, "resets_at": None, "elapsed_pct": None})

    def test_missing_windows_are_none(self):
        self.assertEqual(parse_usage({"five_hour": None}), {"session": None, "week": None})
        self.assertEqual(claude_view({"session": None, "week": None}, NOW), {"session": None, "week": None})

    def test_window_without_reset_time_keeps_its_value(self):
        usage = parse_usage({"five_hour": {"utilization": 3.5, "resets_at": None}})
        self.assertEqual(claude_view(usage, NOW)["session"], {"pct": 4, "resets_at": None})

    def test_request(self):
        self.assertEqual(USAGE_URL, "https://api.anthropic.com/api/oauth/usage")
        self.assertEqual(
            usage_headers("tok"),
            {"Authorization": "Bearer tok", "anthropic-beta": "oauth-2025-04-20"},
        )


class ReadTokenTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write_creds(self, text):
        (self.home / ".claude").mkdir(exist_ok=True)
        (self.home / ".claude" / ".credentials.json").write_text(text)

    def test_read_token_from_keychain_on_macos(self):
        run = FakeRun(stdout=CREDS + "\n")
        self.assertEqual(read_token("darwin", self.home, run=run), "tok")
        self.assertEqual(run.calls, [["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"]])

    def test_read_token_falls_back_to_credentials_file(self):
        self.write_creds(CREDS)
        self.assertEqual(read_token("darwin", self.home, run=FakeRun(returncode=44)), "tok")

    def test_read_token_on_windows_never_runs_security(self):
        self.write_creds(CREDS)
        run = FakeRun(stdout=CREDS)
        self.assertEqual(read_token("win32", self.home, run=run), "tok")
        self.assertEqual(run.calls, [])

    def test_keychain_command_that_cannot_run_falls_back(self):
        def broken(cmd, **kwargs):
            raise FileNotFoundError("security")
        self.write_creds(CREDS)
        self.assertEqual(read_token("darwin", self.home, run=broken), "tok")

    def test_read_token_returns_none_when_missing_or_malformed(self):
        self.assertIsNone(read_token("win32", self.home))
        for bad in ("{not json", '{"claudeAiOauth": {}}', "[]", '{"claudeAiOauth": {"accessToken": ""}}'):
            with self.subTest(bad=bad):
                self.write_creds(bad)
                self.assertIsNone(read_token("win32", self.home))


if __name__ == "__main__":
    unittest.main()
