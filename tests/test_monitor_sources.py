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


class MigratedSourceTests(unittest.TestCase):
    def test_redirect_fixture_has_no_path_tokens(self):
        body = (FIXTURES / "antigravity-ide-skills-redirect.html").read_text(encoding="utf-8")
        self.assertIn('http-equiv="refresh"', body)
        self.assertEqual(set(), MONITOR.extract_tokens(MONITOR.normalize(body)))

    def test_source_endpoints_and_precise_memory_tokens(self):
        sources = {f"{tool}/{name}": url for tool, name, url in MONITOR.SOURCES}
        self.assertNotIn("antigravity/ide-skills", sources)
        self.assertEqual("https://antigravity.google/changelog", sources["antigravity/changelog"])
        self.assertEqual("https://antigravity.google/docs/skills.md", sources["antigravity/skills"])
        self.assertNotIn("antigravity/rules-workflows", sources)
        self.assertEqual("https://antigravity.google/docs/rules.md", sources["antigravity/rules"])
        for name in ("settings", "memory", "skills", "hooks", "desktop", "claude-directory"):
            self.assertEqual(f"https://code.claude.com/docs/en/{name}.md", sources[f"claude-code/{name}"])
        fixtures = json.loads((FIXTURES / "monitor-migrated-sources.json").read_text(encoding="utf-8"))
        baseline = MONITOR.load_baseline()["sources"]
        expected = {
            "antigravity/skills": {"~/.gemini/config/skills/", "~/.gemini/antigravity-cli/skills/",
                                   "~/.gemini/antigravity/skills/"},
            "claude-code/claude-directory": {".claude/agent-memory/", ".claude/agent-memory-local/"},
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
        sources = MONITOR.load_baseline()["sources"]
        self.assertNotIn("antigravity/rules-workflows", sources)
        self.assertTrue(precise_paths <= set(sources["antigravity/rules"]["tokens"]))
        redirect = (FIXTURES / "antigravity-rules-redirect.html").read_text(encoding="utf-8")
        self.assertEqual(set(), MONITOR.extract_tokens(MONITOR.normalize(redirect)))

    def _replay(self, redirect_key=None, *, http_error=False, dry_run=True, update_other=False):
        baseline = MONITOR.load_baseline()
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

    def test_all_sources_success_clears_failure_signal(self):
        self.assertNotIn("[SIGNAL: CHECK_FAILED]", self._replay()[0])

    def test_redirect_regression_still_fails_and_preserves_baseline(self):
        report, _ = self._replay("antigravity/skills")
        self.assertIn("[SIGNAL: CHECK_FAILED]", report)
        self.assertIn("本次保留舊基準", report)
        self.assertNotIn("**消失**", report)

    def test_rules_failure_preserves_entry_when_successful_source_is_written(self):
        before = MONITOR.load_baseline()
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


if __name__ == "__main__":
    unittest.main()
