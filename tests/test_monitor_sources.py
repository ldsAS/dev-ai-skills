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

    def _replay(self, redirect_key=None):
        baseline = MONITOR.load_baseline()
        by_url = {url: f"{tool}/{name}" for tool, name, url in MONITOR.SOURCES}
        redirect = (FIXTURES / "antigravity-ide-skills-redirect.html").read_text(encoding="utf-8")
        def fetch(url):
            key = by_url[url]
            return redirect if key == redirect_key else " ".join(baseline["sources"][key]["tokens"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            path.write_text(json.dumps(baseline), encoding="utf-8")
            before = path.read_bytes()
            out = StringIO()
            with (mock.patch.object(MONITOR, "BASELINE_PATH", str(path)),
                  mock.patch.object(MONITOR, "fetch", side_effect=fetch),
                  mock.patch.object(MONITOR, "NPM_PACKAGES", {}),
                  mock.patch.object(MONITOR, "fetch_antigravity_version", return_value=None),
                  mock.patch.object(sys, "argv", ["check_updates.py", "--dry-run"]), redirect_stdout(out)):
                MONITOR.main()
            self.assertEqual(before, path.read_bytes())
        return out.getvalue()

    def test_all_sources_success_clears_failure_signal(self):
        self.assertNotIn("[SIGNAL: CHECK_FAILED]", self._replay())

    def test_redirect_regression_still_fails_and_preserves_baseline(self):
        report = self._replay("antigravity/skills")
        self.assertIn("[SIGNAL: CHECK_FAILED]", report)
        self.assertIn("本次保留舊基準", report)
        self.assertNotIn("**消失**", report)


if __name__ == "__main__":
    unittest.main()
