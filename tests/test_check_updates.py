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

    def test_trailing_slash_alias_does_not_alert_or_write_baseline(self):
        baseline = self._baseline()
        baseline["sources"][self.source_key]["tokens"].append(".claude/skills/")

        report, before, after = self._run(
            baseline=baseline,
            source_text=".claude/settings.json .claude/skills",
        )

        self.assertIn("無異動", report)
        self.assertNoUpdateSignals(report)
        self.assertEqual(before, after)

    def test_trailing_slash_alias_does_not_hide_real_child_change(self):
        baseline = self._baseline()
        baseline["sources"][self.source_key]["tokens"].append(".claude/skills/")

        report, _, _ = self._run(
            baseline=baseline,
            source_text=(
                ".claude/settings.json .claude/skills "
                ".claude/skills/new/SKILL.md"
            ),
        )

        self.assertIn("`.claude/skills/new/SKILL.md`", report)
        self.assertIn("[SIGNAL: UPDATE_DETECTED]", report)
        self.assertNotIn("**新增**：`.claude/skills`", report)

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


class TokenExtractionTests(unittest.TestCase):
    """token 抽取的排序不變式 —— 漏列長名會造成靜默截短，不會報錯。"""

    def test_trailing_slash_aliases_compare_equal_in_both_directions(self):
        cases = (
            ({".claude/skills"}, {".claude/skills/"}),
            ({"~/.claude/skills/"}, {"~/.claude/skills"}),
        )
        for current, previous in cases:
            self.assertEqual(([], []), MONITOR.token_changes(current, previous))

    def test_longer_dot_names_precede_their_prefixes(self):
        """若 A 是 B 的前綴，B 必須排在 A 之前，否則 alternation 會先命中 A。"""
        names = MONITOR.DOT_NAMES.split("|")
        for i, short in enumerate(names):
            for j, long_ in enumerate(names):
                if long_ != short and long_.startswith(short):
                    self.assertLess(
                        j, i,
                        f"{long_!r} 必須排在 {short!r} 之前，否則 .{long_} 會被截成 .{short}",
                    )

    def test_ignore_file_names_are_not_truncated(self):
        """各工具的 *ignore 檔名必須完整抽出，不可被較短的工具名吃掉。"""
        cases = {
            "files that were in your .antigravityignore.": ".antigravityignore",
            "see .geminiignore for details": ".geminiignore",
            "the .codexignore file": ".codexignore",
        }
        for text, expected in cases.items():
            self.assertEqual({expected}, MONITOR.extract_tokens(text), msg=text)

    def test_dot_names_require_a_right_boundary(self):
        """未知長名不可被靜默截成已知 dot-name token。"""
        cases = (
            ".antigravityignored",
            ".antigravity-new-file",
            ".antigravityignore.bak",
            ".agentsfoo",
            ".geminiwhatever",
            ".codexignore.bak",
        )
        for text in cases:
            self.assertEqual(set(), MONITOR.extract_tokens(text), msg=text)

    def test_dot_name_paths_still_extract_with_the_boundary(self):
        """右側邊界不可擋住合法的相對、家目錄與嵌套路徑。"""
        cases = (
            "~/.claude/projects/demo.json",
            ".agents/skills/example/SKILL.md",
            ".codex/hooks.json",
            "../.gemini/settings.json",
        )
        for text in cases:
            self.assertEqual({text}, MONITOR.extract_tokens(text), msg=text)

    def test_context_uses_the_exact_token_match(self):
        """短 token 的上下文不可誤指向較早出現的長路徑。"""
        text = (
            ".claude/skills/deploy/SKILL.md "
            + ("x" * 300)
            + " run claude plugin validate .claude/skills for project skills"
        )

        context = MONITOR.context_for(text, ".claude/skills", window=45)

        self.assertIn("plugin validate .claude/skills", context)
        self.assertNotIn("deploy/SKILL.md", context)


if __name__ == "__main__":
    unittest.main()
