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
                    ".agents/skills.json", ".agents/rules.json", "apps/web/.agents/skills.json",
                    ".agents/agents.json", ".agents/plugins.json",
                    ".agents/rules/guide.md", ".agents/skills/foo/SKILL.md",
                    ".agents/plugins/guide.md", ".agents/agents/x/agent.json",
                )] + [(path, True) for path in (
                    ".agents/skills.json.bak", ".agents/agents.json.bak", ".agents/plugins.json.bak",
                    ".agents/rules/ORIGINAL_REQUEST.md", ".agents/skills/foo/ORIGINAL_REQUEST.md",
                    ".agents/plugins/ORIGINAL_REQUEST.md", ".agents/agents/x/ORIGINAL_REQUEST.md",
                )]
                self.check_cases(variant, template, cases)



class RepoGitignoreTests(unittest.TestCase):
    """本 repo 根目錄的 .gitignore 必須套用自己的範本（2026-11-27 起）。

    建 repo 時這裡整包排除 `.claude/` 等 AI 資料夾，之後校正只改了範本，
    這裡從未被檢查，因此走樣了七個月。
    """

    REPO = (ROOT / ".gitignore").read_text(encoding="utf-8")

    def problems(self, repo_text):
        return VERIFIER.check_repo_gitignore(repo_text=repo_text)

    def test_repo_gitignore_matches_template(self):
        self.assertEqual([], VERIFIER.check_repo_gitignore())

    def test_reintroducing_a_blanket_claude_rule_is_caught(self):
        text = self.REPO.replace(".claude/*\n", ".claude/\n", 1)
        self.assertNotEqual(text, self.REPO)
        problems = self.problems(text)
        self.assertTrue(any(".claude 規則與 generic 範本不同步" in p for p in problems), problems)
        self.assertTrue(any(p.startswith(".claude/settings.json：預期放行") for p in problems), problems)

    def test_dropping_an_allowlist_is_caught(self):
        text = self.REPO.replace("!.codex/config.toml\n", "", 1)
        self.assertNotEqual(text, self.REPO)
        problems = self.problems(text)
        self.assertTrue(any("缺少 ['!.codex/config.toml']" in p for p in problems), problems)

    def test_reordering_within_a_group_is_caught(self):
        text = self.REPO.replace("!.claude/skills/\n.claude/skills/*\n",
                                 ".claude/skills/*\n!.claude/skills/\n", 1)
        self.assertNotEqual(text, self.REPO)
        self.assertTrue(any("順序不同" in p for p in self.problems(text)))

    def test_missing_secret_rules_leave_allowlisted_dirs_unprotected(self):
        text = self.REPO.replace("\n.env\n", "\n", 1)
        self.assertNotEqual(text, self.REPO)
        problems = self.problems(text)
        self.assertTrue(any("缺少範本的機密規則 .env" in p for p in problems), problems)
        self.assertTrue(any(p.startswith(".claude/hooks/.env：預期擋下") for p in problems), problems)

    def test_group_order_may_differ_between_tools(self):
        # antigravity 版把自家工具排在最前面；各工具的規則互不影響，不算走樣。
        text = VERIFIER.extract_template("antigravity")
        self.assertNotEqual(VERIFIER.ai_rule_groups(text), {})
        self.assertEqual(VERIFIER.ai_rule_groups(VERIFIER.extract_template("generic")),
                         VERIFIER.ai_rule_groups(text))

    def test_repo_keeps_its_own_skill_copy_out_of_agents_skills(self):
        # 2026-08-04 Codex 回覆的決定：技能原始檔在 skills/，不另放同名專案層副本。
        self.assertIn((".agents/skills/ai-git-ignore-strategy/SKILL.md", True), VERIFIER.REPO_CASES)


if __name__ == "__main__":
    unittest.main()
