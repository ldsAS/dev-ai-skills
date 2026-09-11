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


class MonitorRunMixin:
    """離線跑完 main() 的共用骨架（不是 TestCase，避免被重複蒐集）。"""

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
        claims_text=None,
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

        # 預設指向不存在的帳本（多數測試不關心主張比對）；
        # 給了 claims_text 就寫成真檔，讓報告走完整的 claims_for_token() 流程。
        claims_path = Path(temp_dir.name) / "CLAIMS.md"
        if claims_text is None:
            claims_path = Path(temp_dir.name) / "missing.md"
        else:
            claims_path.write_text(claims_text, encoding="utf-8", newline="\n")

        def fake_fetch(_url):
            if source_error:
                raise RuntimeError(source_error)
            return self.source_text if source_text is None else source_text

        argv = ["check_updates.py"] + (["--dry-run"] if dry_run else [])
        output = StringIO()
        with (
            mock.patch.object(MONITOR, "BASELINE_PATH", str(baseline_path)),
            mock.patch.object(MONITOR, "CLAIMS_PATH", str(claims_path)),
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


class CheckUpdatesTests(MonitorRunMixin, unittest.TestCase):
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


CLAIMS_FIXTURE = """
| ID | 路徑 | 主張 | 依據 | 取證日 | 版本 | 狀態 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-02 | `.claude/settings.json` | 團隊共用設定 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-06 | `.claude/skills/` | 需逐案確認 | 官方文件 | 2026-07-29 | — | 已驗證 |
| C-62 | `.claude`（路徑本身作為 symlink） | 不要提交 symlink | 官方 CHANGELOG | 2026-08-03 | — | 已驗證 |
| C-23 | `.geminiignore` | 與 .gitignore 同性質 | 官方文件 | 2026-07-30 | — | 已驗證 |
"""


class ClaimMatchingTests(unittest.TestCase):
    """token ↔ 帳本比對的語彙規則（Issue #12 → C-98 前導斜線、C-99 單段扇出）。"""

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "CLAIMS.md"
        path.write_text(CLAIMS_FIXTURE, encoding="utf-8", newline="\n")
        patcher = mock.patch.object(MONITOR, "CLAIMS_PATH", str(path))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.claims = MONITOR.load_claims()

    def _ids(self, token):
        return [c["id"] for c in MONITOR.claims_for_token(token, self.claims)]

    def test_leading_slash_token_matches_the_same_claims_as_the_bare_form(self):
        """C-98：佔位符前綴切掉後留下的 `/` 不可讓 token 對不到主張。

        把 `_norm_path()` 的 `strip("/")` 還原成 `rstrip("/")`，本測試轉紅。
        """
        self.assertEqual(self._ids(".claude/skills/"), self._ids("/.claude/skills/"))
        self.assertIn("C-06", self._ids("/.claude/skills/"))

    def test_single_segment_token_does_not_fan_out_to_child_claims(self):
        """C-99：`.claude/` 不可把它底下每一條主張都標成受影響。

        這正是 Issue #12 的假陽性 —— 官方 skills 頁只是改寫行文、不再出現裸
        `.claude/`，10 條主張卻同時被報成「原依據可能已不成立」。
        移除 `claims_for_token()` 的單段守衛，本測試轉紅。
        """
        self.assertNotIn("C-02", self._ids(".claude/"))
        self.assertNotIn("C-06", self._ids(".claude/"))

    def test_single_segment_token_still_matches_a_claim_on_that_path_itself(self):
        """扇出收斂後仍須命中以該單段路徑本身為主張者，否則是矯枉過正。"""
        self.assertEqual(["C-62"], self._ids(".claude/"))
        self.assertEqual(["C-62"], self._ids(".claude"))
        self.assertEqual(["C-23"], self._ids(".geminiignore"))

    def test_multi_segment_tokens_keep_bidirectional_prefix_matching(self):
        """收斂只針對單段 token；多段 token 的雙向前綴比對必須原樣保留。"""
        self.assertIn("C-06", self._ids(".claude/skills/verify/SKILL.md"))
        self.assertIn("C-02", self._ids(".claude/settings.json"))


class Issue12ReplayTests(MonitorRunMixin, unittest.TestCase):
    """把 Issue #12 的兩個訊號放回完整報告流程，確認措辭不再誤導。"""

    def _replay(self):
        baseline = self._baseline()
        baseline["sources"][self.source_key]["tokens"] = [
            ".claude/",
            ".claude/settings.json",
            ".claude/skills/",
        ]
        return self._run(
            baseline=baseline,
            claims_text=CLAIMS_FIXTURE,
            source_text=(
                ".claude/settings.json .claude/skills/ "
                "| Nested | `<subdir>/.claude/skills/<skill-name>/SKILL.md` |"
            ),
        )

    def test_both_issue_12_tokens_are_still_detected(self):
        """兩項修正都只改「怎麼歸屬」，不可讓異動本身變得偵測不到。"""
        report, _, _ = self._replay()

        self.assertIn("**消失**：`.claude/`", report)
        self.assertIn("**新增**：`/.claude/skills/`", report)
        self.assertIn("[SIGNAL: UPDATE_DETECTED]", report)

    def test_leading_slash_token_is_not_filed_as_an_unknown_path(self):
        """C-98：`/.claude/skills/` 應歸到 C-06，不該再落進「查無對應主張」區。"""
        report, _, _ = self._replay()

        self.assertIn("**新增**：`/.claude/skills/` → `C-06`", report)
        self.assertNotIn("帳本中查無對應主張的新路徑", report)

    def test_bare_directory_removal_does_not_flag_child_claims(self):
        """C-99：`.claude/` 消失只該牽動 C-62，不該連 C-02、C-06 一起標記。"""
        report, _, _ = self._replay()

        self.assertIn("單段目錄語彙訊號", report)
        # 整條 C-02 不該出現 —— 它只因為住在 `.claude/` 底下而被連坐
        self.assertNotIn("**C-02**", report)
        # C-06 仍會出現，但觸發原因必須是 `/.claude/skills/` 新增（C-98），
        # 不是 `.claude/` 消失；後者才是 Issue #12 誤導人的地方
        self.assertIn("- **C-06**", report)
        c06 = report.split("- **C-06**", 1)[1].split("- **C-", 1)[0]
        self.assertIn("`/.claude/skills/` 新增", c06)
        self.assertNotIn("`.claude/` 消失", c06)


if __name__ == "__main__":
    unittest.main()
