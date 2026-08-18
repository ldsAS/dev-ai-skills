import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "monitor_ci_policy.py"
SPEC = importlib.util.spec_from_file_location("monitor_ci_policy", MODULE_PATH)
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)


class AnalyzeReportTests(unittest.TestCase):
    def test_no_signal_is_healthy(self):
        result = POLICY.analyze_report("## no changes\n", 0)

        self.assertFalse(result["updates"])
        self.assertFalse(result["failure"])
        self.assertFalse(result["should_fail"])
        self.assertEqual([], result["issue_kinds"])

    def test_dual_signal_selects_both_issue_types_and_fails(self):
        report = f"{POLICY.UPDATE_SIGNAL}\n{POLICY.FAILURE_SIGNAL}\n"
        result = POLICY.analyze_report(report, 0)

        self.assertEqual(["update", "failure"], result["issue_kinds"])
        self.assertTrue(result["updates"])
        self.assertTrue(result["failure"])
        self.assertTrue(result["should_fail"])

    def test_nonzero_exit_is_a_failure_without_report_signal(self):
        result = POLICY.analyze_report("traceback was appended\n", 2)

        self.assertTrue(result["failure"])
        self.assertEqual(["failure"], result["issue_kinds"])

    def test_analyze_cli_writes_expected_github_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "report.md"
            output = Path(temp_dir) / "github-output.txt"
            report.write_text(
                f"{POLICY.UPDATE_SIGNAL}\n{POLICY.BASELINE_SIGNAL}\n",
                encoding="utf-8",
            )

            from contextlib import redirect_stdout
            from io import StringIO

            with redirect_stdout(StringIO()):
                exit_code = POLICY.main([
                    "analyze", "--report", str(report), "--exit-code", "0",
                    "--github-output", str(output),
                ])
            values = dict(
                line.split("=", 1)
                for line in output.read_text(encoding="utf-8").splitlines()
            )

        self.assertEqual(0, exit_code)
        self.assertEqual("true", values["updates"])
        self.assertEqual("true", values["baseline"])
        self.assertEqual("false", values["failure"])
        self.assertEqual("update", values["issue_kinds"])


class RecoveryTargetTests(unittest.TestCase):
    def setUp(self):
        self.title = "⚠️ AI 工具異動檢查失敗"

    def test_zero_matches(self):
        self.assertEqual([], POLICY.recovery_targets([], self.title))

    def test_one_exact_open_match(self):
        issues = [{"number": 8, "title": self.title, "state": "OPEN"}]

        self.assertEqual([8], POLICY.recovery_targets(issues, self.title))

    def test_all_exact_open_matches_are_returned(self):
        issues = [
            {"number": 8, "title": self.title, "state": "OPEN"},
            {"number": 9, "title": self.title, "state": "open"},
            {"number": 10, "title": self.title + " copy", "state": "OPEN"},
            {"number": 11, "title": self.title, "state": "CLOSED"},
        ]

        self.assertEqual([8, 9], POLICY.recovery_targets(issues, self.title))

    def test_targets_cli_prints_each_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            issues_path = Path(temp_dir) / "issues.json"
            issues_path.write_text(
                json.dumps([
                    {"number": 12, "title": self.title, "state": "OPEN"},
                    {"number": 13, "title": self.title, "state": "OPEN"},
                ]),
                encoding="utf-8",
            )

            from contextlib import redirect_stdout
            from io import StringIO

            output = StringIO()
            with redirect_stdout(output):
                exit_code = POLICY.main([
                    "targets", "--issues", str(issues_path), "--title", self.title,
                ])

        self.assertEqual(0, exit_code)
        self.assertEqual(["12", "13"], output.getvalue().splitlines())


if __name__ == "__main__":
    unittest.main()
