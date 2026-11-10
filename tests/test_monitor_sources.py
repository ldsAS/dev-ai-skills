import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("monitor", ROOT / "scripts/check_updates.py")
MONITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MONITOR)
FIXTURES = ROOT / "tests/fixtures"
# 凍結的 baseline 快照。scripts/last_checked.json 由機器人每日改寫，且機器人的 push
# 不會觸發 CI；測試若讀 live baseline，上游改版就會讓 main 靜默變紅（2026-10-21 起
# claude-directory 改版即是如此）。新增監控來源時，請一併在此快照補上該來源。
BASELINE = json.loads((FIXTURES / "monitor-baseline.json").read_text(encoding="utf-8"))


class MigratedSourceTests(unittest.TestCase):
    def test_redirect_fixture_has_no_path_tokens(self):
        body = (FIXTURES / "antigravity-ide-skills-redirect.html").read_text(encoding="utf-8")
        self.assertIn('http-equiv="refresh"', body)
        self.assertEqual(set(), MONITOR.extract_tokens(MONITOR.normalize(body)))

    def test_source_endpoints_and_precise_memory_tokens(self):
        sources = {f"{tool}/{name}": url for tool, name, url in MONITOR.SOURCES}
        self.assertEqual(31, len(MONITOR.SOURCES))
        self.assertEqual(len(MONITOR.SOURCES), len(sources))
        self.assertNotIn("antigravity/ide-skills", sources)
        self.assertEqual("https://antigravity.google/docs/changelog.md", sources["antigravity/changelog"])
        self.assertEqual(MONITOR.ANTIGRAVITY_CHANGELOG, sources["antigravity/changelog"])
        self.assertEqual("https://antigravity.google/docs/skills.md", sources["antigravity/skills"])
        self.assertNotIn("antigravity/rules-workflows", sources)
        self.assertEqual("https://antigravity.google/docs/rules.md", sources["antigravity/rules"])
        for name in ("settings", "memory", "skills", "hooks", "desktop", "claude-directory", "sub-agents"):
            self.assertEqual(f"https://code.claude.com/docs/en/{name}.md", sources[f"claude-code/{name}"])
        fixtures = json.loads((FIXTURES / "monitor-migrated-sources.json").read_text(encoding="utf-8"))
        self.assertEqual("https://code.visualstudio.com/docs/copilot/customization/custom-agents",
                         sources["copilot/custom-agents"])
        baseline = BASELINE["sources"]
        expected = {
            "antigravity/skills": {"~/.gemini/config/skills/", "~/.gemini/antigravity-cli/skills/",
                                   "~/.gemini/antigravity/skills/"},
            # C-105 的見證自 claude-directory 移到 sub-agents（2026-10-21 官方改版）。
            "claude-code/sub-agents": {".claude/agent-memory/", ".claude/agent-memory-local/"},
            # C-73 的見證自 customization 總覽移到 custom-agents（2026-11-05 官方改版）。
            "copilot/custom-agents": {".github/agents/planner.agent.md"},
            "claude-code/desktop": {".claude/launch.json"},
        }
        for key, paths in expected.items():
            with self.subTest(source=key):
                self.assertTrue(paths <= MONITOR.extract_tokens(MONITOR.normalize(fixtures[key])))
                self.assertTrue(paths <= set(baseline[key]["tokens"]))

    def test_rules_fixture_and_baseline_include_precise_paths(self):
        text = (FIXTURES / "antigravity-rules.md").read_text(encoding="utf-8")
        tokens = MONITOR.extract_tokens(MONITOR.normalize(text))
        precise_paths = {"/.agents/AGENTS.md", "/.agents/GEMINI.md", ".agents/rules.json"}
        self.assertTrue(precise_paths <= tokens)
        sources = BASELINE["sources"]
        self.assertNotIn("antigravity/rules-workflows", sources)
        self.assertTrue(precise_paths <= set(sources["antigravity/rules"]["tokens"]))
        redirect = (FIXTURES / "antigravity-rules-redirect.html").read_text(encoding="utf-8")
        self.assertEqual(set(), MONITOR.extract_tokens(MONITOR.normalize(redirect)))

    def _replay(self, redirect_key=None, *, http_error=False, dry_run=True, update_other=False):
        baseline = json.loads(json.dumps(BASELINE))
        by_url = {url: f"{tool}/{name}" for tool, name, url in MONITOR.SOURCES}
        fixture = "antigravity-rules-redirect.html" if redirect_key == "antigravity/rules" else "antigravity-ide-skills-redirect.html"
        redirect = (FIXTURES / fixture).read_text(encoding="utf-8")
        def fetch(url):
            key = by_url[url]
            if key == redirect_key:
                if http_error:
                    with HTTPError(url, 404, "Not Found", {}, None) as error:
                        raise error
                return redirect
            body = " ".join(baseline["sources"][key]["tokens"])
            if update_other and key == "antigravity/skills":
                body += " .agents/skills/migration-probe/SKILL.md"
            return body
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            path.write_text(json.dumps(baseline), encoding="utf-8")
            before = path.read_bytes()
            out = StringIO()
            with (mock.patch.object(MONITOR, "BASELINE_PATH", str(path)),
                  mock.patch.object(MONITOR, "fetch", side_effect=fetch),
                  mock.patch.object(MONITOR, "NPM_PACKAGES", {}),
                  mock.patch.object(MONITOR, "fetch_antigravity_version", return_value=None),
                  mock.patch.object(sys, "argv", ["check_updates.py"] + (["--dry-run"] if dry_run else [])), redirect_stdout(out)):
                MONITOR.main()
            if dry_run:
                self.assertEqual(before, path.read_bytes())
            after = json.loads(path.read_text(encoding="utf-8"))
        return out.getvalue(), after

    def test_frozen_baseline_covers_exactly_the_monitored_sources(self):
        # 新增或移除來源時，快照必須同步更新；否則 replay 測試會在缺少來源時誤報失敗。
        self.assertEqual({f"{tool}/{name}" for tool, name, _url in MONITOR.SOURCES},
                         set(BASELINE["sources"]))
        self.assertEqual(MONITOR.SCHEMA_VERSION, BASELINE["schema"])

    def test_baselines_hold_only_canonical_tokens(self):
        # 抽取結果一律以 `/` 分隔；殘留反斜線 token 會在下一輪被誤報成「消失」。
        for name, data in (("frozen", BASELINE), ("live", MONITOR.load_baseline())):
            for key, entry in data["sources"].items():
                with self.subTest(baseline=name, source=key):
                    self.assertEqual([], [t for t in entry["tokens"] if "\\" in t])

    def test_all_sources_success_clears_failure_signal(self):
        self.assertNotIn("[SIGNAL: CHECK_FAILED]", self._replay()[0])

    def test_redirect_regression_still_fails_and_preserves_baseline(self):
        report, _ = self._replay("antigravity/skills")
        self.assertIn("[SIGNAL: CHECK_FAILED]", report)
        self.assertIn("本次保留舊基準", report)
        self.assertNotIn("**消失**", report)

    def test_rules_failure_preserves_entry_when_successful_source_is_written(self):
        before = BASELINE
        for http_error in (False, True):
            with self.subTest(http_error=http_error):
                report, after = self._replay("antigravity/rules", http_error=http_error,
                                             dry_run=False, update_other=True)
                self.assertIn("[SIGNAL: CHECK_FAILED]", report)
                self.assertIn("[SIGNAL: BASELINE_CHANGED]", report)
                self.assertIn("基準線已保留", report)
                self.assertNotIn("**消失**", report)
                self.assertEqual(before["sources"]["antigravity/rules"], after["sources"]["antigravity/rules"])
                expected = json.loads(json.dumps(before))
                expected["sources"]["antigravity/skills"]["tokens"] = sorted(
                    before["sources"]["antigravity/skills"]["tokens"] + [".agents/skills/migration-probe/SKILL.md"])
                self.assertEqual(expected, after)


class DiscoveryManifestTests(unittest.TestCase):
    """來源專屬的推導見證（C-120／C-121；PR #44 review）。"""

    KEY = MONITOR.DISCOVERY_MANIFEST_SOURCE
    PAGE = json.loads((FIXTURES / "monitor-migrated-sources.json").read_text(encoding="utf-8"))[KEY]
    MANIFESTS = {".agents/skills.json", ".agents/rules.json", ".agents/agents.json", ".agents/plugins.json"}

    def tokens(self, page, key=KEY):
        text = MONITOR.normalize(page)
        return MONITOR.extract_tokens(text + MONITOR.derived_path_notes(key, text))

    def test_source_is_monitored_and_page_yields_all_four_manifest_paths(self):
        self.assertIn(self.KEY, {f"{tool}/{name}" for tool, name, _url in MONITOR.SOURCES})
        # 逐字抽取得不到這些完整路徑：頁面把位置與檔名分兩句寫。
        self.assertFalse(self.MANIFESTS & MONITOR.extract_tokens(MONITOR.normalize(self.PAGE)))
        self.assertTrue(self.MANIFESTS <= self.tokens(self.PAGE))
        self.assertTrue(self.MANIFESTS <= set(BASELINE["sources"][self.KEY]["tokens"]))

    def test_notes_add_only_the_derived_paths(self):
        text = MONITOR.normalize(self.PAGE)
        notes = MONITOR.derived_path_notes(self.KEY, text)
        self.assertEqual(self.MANIFESTS, MONITOR.extract_tokens(notes))
        # 同頁表格裡的 hooks.json／mcp_config.json 不在 manifest 清單內，各有自己的主張與見證。
        for other in ("hooks.json", "mcp_config.json"):
            self.assertIn(f"`{other}`", self.PAGE)
            self.assertNotIn(other, notes)
        self.assertEqual(4, notes.count(MONITOR.DERIVED_NOTE))

    def test_no_placement_sentence_means_no_derivation(self):
        page = self.PAGE.replace("Put a manifest in a `.agents/` folder", "Keep a manifest next to your code")
        self.assertNotEqual(page, self.PAGE)
        self.assertEqual("", MONITOR.derived_path_notes(self.KEY, MONITOR.normalize(page)))
        self.assertFalse(self.MANIFESTS & self.tokens(page))

    def test_no_manifest_list_means_no_derivation(self):
        page = self.PAGE.replace("each have their own manifest:", "can each be listed, for example in")
        self.assertNotEqual(page, self.PAGE)
        self.assertFalse(self.MANIFESTS & self.tokens(page))

    def test_renamed_or_removed_manifest_changes_the_token_set(self):
        renamed = self.tokens(self.PAGE.replace("`agents.json`", "`subagents.json`"))
        self.assertIn(".agents/subagents.json", renamed)
        self.assertNotIn(".agents/agents.json", renamed)
        removed = self.tokens(self.PAGE.replace("`agents.json`, and `plugins.json`", "and `plugins.json`"))
        self.assertEqual(self.MANIFESTS - {".agents/agents.json"}, removed & self.MANIFESTS)

    def test_other_sources_never_derive(self):
        for tool, name, _url in MONITOR.SOURCES:
            key = f"{tool}/{name}"
            if key != self.KEY:
                with self.subTest(source=key):
                    self.assertEqual("", MONITOR.derived_path_notes(key, MONITOR.normalize(self.PAGE)))

    def test_plugin_root_manifests_are_not_workspace_manifests(self):
        # 官方 changelog 原句：外掛根目錄的 agents.json 是另一個檔案，即使出現在本頁也不得推導。
        page = ("Put a manifest in a `.agents/` folder for one project.\n"
                "Added support for a root-level `agents.json` in plugins, so a plugin can declare its "
                "subagents the same way it declares skills and rules with `skills.json` and `rules.json`.")
        self.assertEqual("", MONITOR.derived_path_notes(self.KEY, MONITOR.normalize(page)))

    def run_monitor(self, page, baseline_tokens):
        baseline = {"schema": MONITOR.SCHEMA_VERSION, "versions": {},
                    "sources": {self.KEY: {"tokens": sorted(baseline_tokens)}}}
        tool, name = self.KEY.split("/", 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            path.write_text(json.dumps(baseline), encoding="utf-8")
            out = StringIO()
            with (mock.patch.object(MONITOR, "BASELINE_PATH", str(path)),
                  mock.patch.object(MONITOR, "SOURCES", [(tool, name, "https://example.invalid/discovery")]),
                  mock.patch.object(MONITOR, "fetch", return_value=page),
                  mock.patch.object(MONITOR, "NPM_PACKAGES", {}),
                  mock.patch.object(MONITOR, "fetch_antigravity_version", return_value=None),
                  mock.patch.object(sys, "argv", ["check_updates.py", "--dry-run"]), redirect_stdout(out)):
                MONITOR.main()
        return out.getvalue()

    def test_unchanged_page_raises_no_alert(self):
        report = self.run_monitor(self.PAGE, self.tokens(self.PAGE))
        self.assertIn("## ✅ 無異動", report)
        self.assertNotIn("[SIGNAL:", report)

    def test_removed_manifest_alerts_against_its_ledger_claim(self):
        # 使用正式帳本：這正是 PR #44 review 指出原本不會告警的情境。
        page = self.PAGE.replace("`agents.json`, and `plugins.json`", "and `plugins.json`")
        report = self.run_monitor(page, self.tokens(self.PAGE))
        self.assertIn("- ❌ **消失**：`.agents/agents.json` → `C-121`", report)
        self.assertNotIn("`.agents/plugins.json`", report)
        self.assertIn("[SIGNAL: UPDATE_DETECTED]", report)

    def test_added_derived_path_is_labelled_in_the_report(self):
        report = self.run_monitor(self.PAGE, self.tokens(self.PAGE) - {".agents/plugins.json"})
        self.assertIn("- ✅ **新增**：`.agents/plugins.json` → `C-120`", report)
        added = report.split("`.agents/plugins.json` → `C-120`", 1)[1].split("\n", 2)[1]
        self.assertIn(MONITOR.DERIVED_NOTE, added)

    def test_coverage_counts_both_manifest_claims_as_witnessed(self):
        out = StringIO()
        with (mock.patch.object(MONITOR, "BASELINE_PATH", str(FIXTURES / "monitor-baseline.json")),
              redirect_stdout(out)):
            MONITOR.report_coverage()
        blind, covered = out.getvalue().split("## ✅ 有監控涵蓋", 1)
        for claim in ("C-120", "C-121"):
            with self.subTest(claim=claim):
                self.assertNotIn(f"**{claim}**", blind)
                line = next(l for l in covered.splitlines() if f"**{claim}**" in l)
                self.assertIn(self.KEY, line)


if __name__ == "__main__":
    unittest.main()
