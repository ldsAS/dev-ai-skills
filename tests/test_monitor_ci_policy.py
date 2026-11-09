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
    def test_only_complete_lf_or_crlf_signal_lines_count(self):
        for signal, key in ((POLICY.UPDATE_SIGNAL, "updates"),
                            (POLICY.FAILURE_SIGNAL, "failure"),
                            (POLICY.BASELINE_SIGNAL, "baseline")):
            for text in (signal, signal + "\n", signal + "\r\n"):
                with self.subTest(text=text):
                    self.assertTrue(POLICY.analyze_report(text)[key])
            for text in ("> " + signal, " " + signal, signal + " ", "x" + signal,
                         "&#91;" + signal[1:], "x\u2028" + signal,
                         "x\u0085" + signal, "x\r" + signal, signal + "\r\r\n"):
                with self.subTest(text=text):
                    self.assertFalse(POLICY.analyze_report(text)[key])

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


DUAL_REPORT = """> 🤖 以下摘要由 AI 生成，僅供快速理解。
> 摘要內容

## 🚨 偵測到 AI 工具路徑異動

偵測到官方來源中的候選路徑變動。

### `claude-code` — desktop

- ✅ **新增**：`.claude/` → `C-62`
  > context with ## inside and --- inside

## 📒 受影響的帳本主張

- **C-62** `.claude` — 狀態 已驗證

## 🆕 帳本中查無對應主張的新路徑

- claude-code/desktop: `x`

## ⬆️ 版本跳動（機制可能重構）

- **antigravity**：`2.0.0` → `3.0.0`

## ⚠️ 檢查失敗的來源

- `version/x`：真正的失敗原因

<details><summary>本輪版本取得結果</summary>

- claude-code: `2.1.318`

</details>

[SIGNAL: BASELINE_CHANGED]
[SIGNAL: UPDATE_DETECTED]
[SIGNAL: CHECK_FAILED]

## ❌ 檢查腳本以非 0 狀態結束 (exit 1)

---
由 check-updates.yml 產生。

CC: @owner
"""


class FailureReportTests(unittest.TestCase):
    def test_dual_report_keeps_failure_and_drops_update_sections(self):
        result = POLICY.failure_report(DUAL_REPORT, "41792831833")
        for heading in POLICY.UPDATE_ONLY_HEADINGS:
            self.assertNotIn(heading, result)
        for gone in ("### `claude-code`", "C-62", "context with", "`2.0.0` → `3.0.0`"):
            self.assertNotIn(gone, result)
        for kept in ("> 🤖 以下摘要由 AI 生成", "## ⚠️ 檢查失敗的來源", "真正的失敗原因",
                     "<summary>本輪版本取得結果</summary>", "## ❌ 檢查腳本以非 0 狀態結束",
                     "CC: @owner", "· run 41792831833」issue"):
            self.assertIn(kept, result)
        self.assertEqual(1, result.count("完整內容已送至"))
        # 訊號行原樣保留，下游解析結果不變。
        self.assertEqual(POLICY.analyze_report(DUAL_REPORT), POLICY.analyze_report(result))

    def test_failure_only_report_is_returned_unchanged(self):
        report = DUAL_REPORT.split("## 🚨", 1)[0] + "## ⚠️" + DUAL_REPORT.split("## ⚠️", 1)[1]
        self.assertEqual(report, POLICY.failure_report(report, "1"))

    def test_unknown_heading_is_kept(self):
        report = "## 🚨 偵測到 AI 工具路徑異動\n\nx\n\n## 🔍 未來新增的區段\n\ny\n"
        self.assertIn("## 🔍 未來新增的區段\n\ny", POLICY.failure_report(report, "1"))

    def test_crlf_report_is_filtered(self):
        result = POLICY.failure_report(DUAL_REPORT.replace("\n", "\r\n"), "1")
        self.assertNotIn("C-62", result)
        self.assertIn("真正的失敗原因", result)

    def test_run_id_must_be_digits(self):
        for bad in ("", "12a", "1 2", "../1"):
            with self.subTest(run_id=bad), self.assertRaises(ValueError):
                POLICY.failure_report(DUAL_REPORT, bad)

    def test_headings_match_checker_source_verbatim(self):
        # 標題若在 check_updates.py 改字，denylist 會靜默失效（只會重複，不會漏報）。
        source = (ROOT / "scripts" / "check_updates.py").read_text(encoding="utf-8")
        for heading in POLICY.UPDATE_ONLY_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(f'"{heading}"', source)

    def test_failure_report_cli_writes_filtered_report(self):
        from contextlib import redirect_stdout
        from io import StringIO

        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "report.md"
            report.write_text(DUAL_REPORT, encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                exit_code = POLICY.main(["failure-report", "--report", str(report), "--run-id", "7"])
        self.assertEqual(0, exit_code)
        self.assertEqual(POLICY.failure_report(DUAL_REPORT, "7"), output.getvalue())


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
