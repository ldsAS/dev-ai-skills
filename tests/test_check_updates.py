import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_updates.py"
SPEC = importlib.util.spec_from_file_location("check_updates", MODULE_PATH)
MONITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MONITOR)


class CheckUpdatesTests(unittest.TestCase):
    source_key = "claude-code/settings"
    source_text = ".claude/settings.json"

    def _baseline(self):
        return {
            "schema": MONITOR.SCHEMA_VERSION,
            "versions": {
                "claude-code": "2.1.232",
                "antigravity": "2.8.1",
            },
            "sources": {
                self.source_key: {"tokens": [".claude/settings.json"]},
            },
        }

    def _run(
        self,
        *,
        claude_version="2.1.232",
        antigravity_version="2.8.1",
        source_text=None,
        source_error=None,
        dry_run=False,
        baseline=None,
    ):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        baseline_path = Path(temp_dir.name) / "last_checked.json"
        original = self._baseline() if baseline is None else baseline
        baseline_path.write_text(
            json.dumps(original, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        before = baseline_path.read_bytes()

        def fake_fetch(_url):
            if source_error:
                raise RuntimeError(source_error)
            return self.source_text if source_text is None else source_text

        argv = ["check_updates.py"] + (["--dry-run"] if dry_run else [])
        output = StringIO()
        with (
            mock.patch.object(MONITOR, "BASELINE_PATH", str(baseline_path)),
            mock.patch.object(MONITOR, "CLAIMS_PATH", str(Path(temp_dir.name) / "missing.md")),
            mock.patch.object(
                MONITOR,
                "SOURCES",
                [("claude-code", "settings", "https://example.invalid/settings")],
            ),
            mock.patch.object(MONITOR, "NPM_PACKAGES", {"claude-code": "example"}),
            mock.patch.object(MONITOR, "ALERT_LEVEL", {}),
            mock.patch.object(MONITOR, "fetch", side_effect=fake_fetch),
            mock.patch.object(MONITOR, "fetch_npm_version", return_value=claude_version),
            mock.patch.object(MONITOR, "fetch_antigravity_version", return_value=antigravity_version),
            mock.patch.object(sys, "argv", argv),
            redirect_stdout(output),
        ):
            MONITOR.main()

        return output.getvalue(), before, baseline_path.read_bytes()

    def assertNoUpdateSignals(self, report):
        self.assertNotIn("[SIGNAL: UPDATE_DETECTED]", report)
        self.assertNotIn("[SIGNAL: BASELINE_CHANGED]", report)

    def test_patch_only_is_reference_without_baseline_write(self):
        report, before, after = self._run(claude_version="2.1.233")

        self.assertIn("版本參考（非告警項）", report)
        self.assertNoUpdateSignals(report)
        self.assertEqual(before, after)

    def test_antigravity_minor_is_reference_without_baseline_write(self):
        report, before, after = self._run(antigravity_version="2.9.0")

        self.assertIn("antigravity: `2.8.1` → `2.9.0`", report)
        self.assertIn("相對上次有意義 baseline 的累積值", report)
        self.assertNoUpdateSignals(report)
        self.assertEqual(before, after)

    def test_zero_x_minor_is_not_promoted_to_an_alert(self):
        baseline = self._baseline()
        baseline["versions"]["claude-code"] = "0.146.2"
        report, before, after = self._run(
            baseline=baseline,
            claude_version="0.147.0",
        )

        self.assertIn("claude-code: `0.146.2` → `0.147.0`", report)
        self.assertNoUpdateSignals(report)
        self.assertEqual(before, after)

    def test_zero_x_to_one_x_is_a_major_alert(self):
        baseline = self._baseline()
        baseline["versions"]["claude-code"] = "0.99.0"
        report, _, _ = self._run(baseline=baseline, claude_version="1.0.0")

        self.assertIn("[SIGNAL: UPDATE_DETECTED]", report)
        self.assertIn("[SIGNAL: BASELINE_CHANGED]", report)
        self.assertIn("主版號跨越是低頻人工複驗訊號", report)

    def test_antigravity_major_alert_has_generic_review_prompt(self):
        report, before, after = self._run(antigravity_version="3.0.0")

        self.assertIn("[SIGNAL: UPDATE_DETECTED]", report)
        self.assertIn("[SIGNAL: BASELINE_CHANGED]", report)
        self.assertIn("主版號跨越是低頻人工複驗訊號", report)
        self.assertNotEqual(before, after)

    def test_other_tool_major_alert_has_same_generic_review_prompt(self):
        report, _, _ = self._run(claude_version="3.0.0")

        self.assertIn("[SIGNAL: UPDATE_DETECTED]", report)
        self.assertIn("主版號跨越是低頻人工複驗訊號", report)

    def test_token_addition_is_a_candidate_and_updates_baseline(self):
        report, before, after = self._run(
            source_text=".claude/settings.json .claude/new.json"
        )

        self.assertIn("候選路徑變動", report)
        self.assertIn("[SIGNAL: UPDATE_DETECTED]", report)
        self.assertIn("[SIGNAL: BASELINE_CHANGED]", report)
        self.assertNotEqual(before, after)

    def test_failed_source_keeps_baseline_and_signals_failure(self):
        report, before, after = self._run(source_error="network unavailable")

        self.assertIn("[SIGNAL: CHECK_FAILED]", report)
        self.assertNotIn("[SIGNAL: BASELINE_CHANGED]", report)
        self.assertEqual(before, after)

    def test_dry_run_reports_major_change_without_writing(self):
        report, before, after = self._run(claude_version="3.0.0", dry_run=True)

        self.assertIn("[SIGNAL: UPDATE_DETECTED]", report)
        self.assertIn("[SIGNAL: BASELINE_CHANGED]", report)
        self.assertEqual(before, after)

    def test_new_source_bootstraps_without_update_alert(self):
        baseline = self._baseline()
        baseline["sources"] = {}
        report, before, after = self._run(baseline=baseline)

        self.assertIn("基準線建立", report)
        self.assertNotIn("[SIGNAL: UPDATE_DETECTED]", report)
        self.assertIn("[SIGNAL: BASELINE_CHANGED]", report)
        self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
