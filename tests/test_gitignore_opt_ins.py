"""Exercise optional allowlists while retaining prompt and private-file boundaries."""
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("template_verifier", ROOT / "scripts/verify_gitignore_template.py")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class OptInBoundaryTests(unittest.TestCase):
    def check_cases(self, variant, template, cases):
        with (mock.patch.object(VERIFIER, "extract_template", return_value=template),
              mock.patch.object(VERIFIER, "CASES", cases)):
            self.assertEqual([], VERIFIER.check_variant(variant))

    def test_config_opt_in_keeps_private_content_excluded(self):
        for variant in VERIFIER.variants():
            with self.subTest(variant=variant):
                template = VERIFIER.extract_template(variant)
                template = template.replace("# !.gemini/config.json", "!.gemini/config.json")
                self.check_cases(variant, template, [
                    (".gemini/config.json", False), (".gemini/settings.json", False),
                    (".gemini/tmp/x.json", True), (".gemini/cache/a", True),
                    (".gemini/config.json.bak", True),
                ])

    def test_enabled_agents_allowlists_keep_prompts_excluded(self):
        for variant in VERIFIER.variants():
            with self.subTest(variant=variant):
                template = VERIFIER.extract_template(variant)
                template = template.replace("# !.agents/skills/<project-skill>/", "!.agents/skills/foo/")
                template = template.replace("# !.agents/agents/", "!.agents/agents/")
                template = template.replace(".agents/plugins/*\n", ".agents/plugins/*\n!.agents/plugins/**\n")
                cases = [(path, False) for path in (
                    ".agents/rules/guide.md", ".agents/skills/foo/SKILL.md",
                    ".agents/plugins/guide.md", ".agents/agents/x/agent.json",
                )] + [(path, True) for path in (
                    ".agents/rules/ORIGINAL_REQUEST.md", ".agents/skills/foo/ORIGINAL_REQUEST.md",
                    ".agents/plugins/ORIGINAL_REQUEST.md", ".agents/agents/x/ORIGINAL_REQUEST.md",
                )]
                self.check_cases(variant, template, cases)


if __name__ == "__main__":
    unittest.main()
