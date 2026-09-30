import html
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


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = load("changelog_monitor", "check_updates.py")
POLICY = load("changelog_policy", "monitor_ci_policy.py")
FIXTURE = (ROOT / "tests/fixtures/antigravity-changelog.md").read_text(encoding="utf-8")
REDIRECT = (ROOT / "tests/fixtures/antigravity-changelog-redirect.html").read_text(encoding="utf-8")
HEADER = "## Antigravity 2.0\n\n"


def record(version="2.18.1", released_on="September 28, 2026", *, latest=False):
    label = "Latest\n\n" if latest else ""
    return (f'### [v{version}](/releases?tab=hub&version={version} "View release {version}")\n\n'
            f"{label}{released_on}\n\n")


class ChangelogParserTests(unittest.TestCase):
    def test_four_surfaces_select_product_and_return_observed_metadata(self):
        parsed = M.parse_antigravity_changelog(FIXTURE)
        self.assertEqual("2.18.1", parsed.version)
        self.assertEqual("Antigravity 2.0", parsed.section)
        self.assertEqual("September 28, 2026", parsed.released_on)
        self.assertEqual(10, parsed.line)
        self.assertTrue({".agents/agents/", ".agents/skills/", "~/.gemini/config/plugins"}
                        <= M.extract_tokens(M.normalize(FIXTURE)))

    def test_ide_high_version_cannot_override_product(self):
        body = HEADER + record() + "## Antigravity IDE\n\n" + record("2.99.0").replace("tab=hub", "tab=ide")
        self.assertEqual("2.18.1", M.parse_antigravity_changelog(body).version)

    def test_hub_link_on_other_surface_cannot_override_product(self):
        body = "## Antigravity SDK\n\n" + record("9.99.0") + HEADER + record()
        self.assertEqual("2.18.1", M.parse_antigravity_changelog(body).version)

    def test_numeric_order_and_date_follow_selected_record_not_latest_marker(self):
        body = HEADER + record("2.9.0", "January 9, 2026", latest=True) + record("2.10.0", "February 10, 2026")
        result = M.parse_antigravity_changelog(body)
        self.assertEqual(("2.10.0", "February 10, 2026"), (result.version, result.released_on))

    def test_future_major_under_known_section_is_valid(self):
        self.assertEqual("3.0.0", M.parse_antigravity_changelog(HEADER + record("3.0.0")).version)

    def test_blank_lines_and_optional_latest(self):
        for latest in (False, True):
            with self.subTest(latest=latest):
                body = (HEADER + record(latest=latest)).replace("\n\n", "\n \n\n")
                self.assertEqual("2.18.1", M.parse_antigravity_changelog(body).version)

    def test_feature_titles_and_body_numbers_are_not_candidates(self):
        body = HEADER + record() + "### Google Antigravity SDK release 9.99.0 updates\n\nv88.0.0\n"
        self.assertEqual("2.18.1", M.parse_antigravity_changelog(body).version)

    def test_candidate_grammar_is_wider_than_valid_release_grammar(self):
        bad_headers = [
            "### v2.19.0", "### 2.19.0", "### [2.19.0]",
            "### [2.19.0](/download#antigravity-app)",
            "### [v2.19](/releases?tab=hub&version=2.19)",
            "### [v2.19.0-rc.1](/releases?tab=hub&version=2.19.0-rc.1)",
            "### [Download](/releases?tab=hub&version=2.19.0)",
        ]
        for bad in bad_headers:
            with self.subTest(heading=bad):
                # The valid older record must not mask the broken newer one.
                body = "# Changelog\n\n" + HEADER + bad + "\n\nOctober 5, 2026\n\n" + record()
                with self.assertRaises(ValueError) as raised:
                    M.parse_antigravity_changelog(body)
                self.assertIn("第 5 行", str(raised.exception))
                self.assertIn(M.report_text(bad), str(raised.exception))

    def test_link_validation_and_malformed_url_retain_header_location(self):
        links = [
            "/releases?tab=ide&version=2.19.0", "/releases?tab=hub&version=2.18.1",
            "/releases?tab=hub&tab=hub&version=2.19.0",
            "/releases?tab=hub&version=2.19.0&version=2.19.0",
            "/releases?tab=&version=2.19.0", "/releases?tab=hub", "/download",
            "https://example.invalid/releases?tab=hub&version=2.19.0",
            "//[bad/releases?tab=hub&version=2.19.0",
        ]
        for link in links:
            with self.subTest(link=link):
                bad = f"### [v2.19.0]({link})"
                with self.assertRaises(ValueError) as raised:
                    M.parse_antigravity_changelog(HEADER + bad + "\n\nOctober 5, 2026\n\n" + record())
                self.assertIn("第 3 行", str(raised.exception))
                self.assertIn(M.report_text(bad), str(raised.exception))

    def test_query_order_and_optional_link_title(self):
        body = HEADER + '### [v2.18.1](/releases?version=2.18.1&tab=hub)\n\nSeptember 28, 2026\n'
        self.assertEqual("2.18.1", M.parse_antigravity_changelog(body).version)

    def test_invalid_dates_fail_without_borrowing_later_date(self):
        for bad_date in ("", "February 30, 2026", "September 31, 2026", "September 28, 0000",
                         "Smarch 1, 2026", "2026-09-28", "Latest", "### Feature\n\nSeptember 28, 2026"):
            with self.subTest(date=bad_date), self.assertRaises(ValueError) as raised:
                M.parse_antigravity_changelog(HEADER + record("2.19.0", bad_date) + record())
            self.assertIn("第 3 行", str(raised.exception))
            self.assertIn("有效英文日期", str(raised.exception))

    def test_corrupt_old_record_is_also_reported_with_global_line(self):
        body = HEADER + record() + record("2.0.1", "February 30, 2026")
        with self.assertRaises(ValueError) as raised:
            M.parse_antigravity_changelog(body)
        self.assertIn("第 7 行", str(raised.exception))
        self.assertIn("v2.0.1", str(raised.exception))

    def test_empty_section_and_missing_date_at_section_boundary_fail(self):
        for body in (HEADER, HEADER + "### [v2.18.1](/releases?tab=hub&version=2.18.1)\n\n## Antigravity IDE\nSeptember 28, 2026"):
            with self.subTest(body=body), self.assertRaises(ValueError):
                M.parse_antigravity_changelog(body)

    def test_missing_duplicate_and_renamed_sections_list_observed_h2(self):
        for body, expected in (("## Antigravity CLI\n" + record(), "Antigravity CLI"),
                               (HEADER + record() + HEADER + record(), "實得 2 個"),
                               ("## Antigravity 3.0\n" + record("3.0.0"), "Antigravity 3.0")):
            with self.subTest(body=body), self.assertRaises(ValueError) as raised:
                M.parse_antigravity_changelog(body)
            self.assertIn(expected, str(raised.exception))
            self.assertIn("第 1 行", str(raised.exception))
            self.assertIn("區段可能改名", str(raised.exception))

    def test_redirect_and_old_release_rows_do_not_fall_back(self):
        for body in (REDIRECT, "2.18.1 September 28, 2026", "", HEADER + "2.18.1 September 28, 2026"):
            with self.subTest(body=body), self.assertRaises(ValueError):
                M.parse_antigravity_changelog(body)

    def test_fenced_fake_sections_and_releases_are_ignored(self):
        for fence in ("```", "~~~~", "   ````"):
            with self.subTest(fence=fence):
                closer = fence.strip()[0] * (len(fence.strip()) + 1)
                code = fence + "markdown\n" + HEADER + record("99.0.0") + closer + "\n"
                body = code + HEADER + record() + code
                self.assertEqual("2.18.1", M.parse_antigravity_changelog(body).version)

    def test_unclosed_wrong_kind_or_short_fence_fails_at_opener(self):
        for opening, closing in (("```", ""), ("~~~", "```"), ("````", "```")):
            with self.subTest(opening=opening, closing=closing), self.assertRaises(ValueError) as raised:
                M.parse_antigravity_changelog(HEADER + record() + opening + "python\n" + closing)
            self.assertIn("第 7 行", str(raised.exception))
            self.assertIn("fence 未閉合", str(raised.exception))

    def test_date_cannot_be_borrowed_across_a_fence(self):
        body = HEADER + record(released_on="```\nSeptember 28, 2026\n```")
        with self.assertRaisesRegex(ValueError, "有效英文日期"):
            M.parse_antigravity_changelog(body)

    def test_safe_text_neutralizes_signals_html_controls_and_long_titles(self):
        raw = '`<b>[SIGNAL: CHECK_FAILED]</b>\r\n[SIGNAL: UPDATE_DETECTED]\x00[SIGNAL: BASELINE_CHANGED]'
        safe = M.report_text(raw)
        self.assertEqual('`<b>[SIGNAL: CHECK_FAILED]</b> [SIGNAL: UPDATE_DETECTED] [SIGNAL: BASELINE_CHANGED]', html.unescape(safe))
        for forbidden in ("[SIGNAL:", "<b>", "`", "\n", "\r", "\x00"):
            self.assertNotIn(forbidden, safe)
        self.assertEqual([], POLICY.analyze_report(safe)["issue_kinds"])
        clipped = M.report_text("x" * 1000 + raw)
        self.assertEqual("x" * 240 + "…（已截斷）", clipped)

    def test_h2_and_release_diagnostics_cannot_inject_ci_signals(self):
        for signal in ("UPDATE_DETECTED", "BASELINE_CHANGED", "CHECK_FAILED"):
            marker = f"[SIGNAL: {signal}]"
            for body in (f"## Missing {marker}\n", HEADER + f"### 2.19.0 {marker}\n" + record()):
                with self.subTest(body=body), self.assertRaises(ValueError) as raised:
                    M.parse_antigravity_changelog(body)
                diagnostic = str(raised.exception)
                self.assertNotIn(marker, diagnostic)
                self.assertIn("第", diagnostic)
                self.assertEqual([], POLICY.analyze_report(diagnostic)["issue_kinds"])
                policy = POLICY.analyze_report(diagnostic + "\n[SIGNAL: CHECK_FAILED]\n")
                self.assertEqual(["failure"], policy["issue_kinds"])
                self.assertFalse(policy["baseline"])

    def test_getter_uses_canonical_body_without_token_normalization(self):
        with mock.patch.object(M, "fetch", return_value=FIXTURE) as fetch, mock.patch.object(M, "normalize", side_effect=AssertionError("version parser must use raw Markdown")):
            self.assertEqual("2.18.1", M.fetch_antigravity_version().version)
        fetch.assert_called_once_with(M.ANTIGRAVITY_CHANGELOG)

    def test_fetch_retries_and_propagates_error(self):
        with mock.patch.object(M.urllib.request, "urlopen", side_effect=OSError("offline")) as request, mock.patch.object(M.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "offline"):
                M.fetch_antigravity_version()
        self.assertEqual(M.RETRIES, request.call_count)


class ChangelogIntegrationTests(unittest.TestCase):
    def run_monitor(self, *, source_body=FIXTURE, getter_body=None, baseline_version="2.18.1",
                    dry_run=False, update_other=False, getter_stub=mock.sentinel.real, npm_value="1.0.0"):
        baseline = {"schema": 2, "versions": {"antigravity": baseline_version, "claude-code": "1.0.0"},
                    "sources": {"antigravity/changelog": {"tokens": sorted(M.extract_tokens(M.normalize(FIXTURE)))},
                                "claude-code/settings": {"tokens": [".claude/settings.json"]}}}
        counts = {"source": 0}

        def fetch(url):
            if url == M.ANTIGRAVITY_CHANGELOG:
                counts["source"] += 1
                body = getter_body if counts["source"] > 1 and getter_body is not None else source_body
                if isinstance(body, Exception):
                    raise body
                return body
            if url == "https://example.invalid/settings":
                return ".claude/settings.json" + (" .claude/new.json" if update_other else "")
            if url == "https://registry.npmjs.org/example/latest":
                return json.dumps({"version": npm_value})
            raise AssertionError(f"unexpected URL {url}")

        with tempfile.TemporaryDirectory(prefix="changelog-test-") as directory:
            path = Path(directory) / "baseline.json"
            path.write_text(json.dumps(baseline) + "\n", encoding="utf-8", newline="\n")
            before = path.read_bytes()
            output = StringIO()
            with (mock.patch.object(M, "BASELINE_PATH", str(path)),
                  mock.patch.object(M, "CLAIMS_PATH", str(Path(directory) / "missing.md")),
                  mock.patch.object(M, "SOURCES", [("antigravity", "changelog", M.ANTIGRAVITY_CHANGELOG),
                                                  ("claude-code", "settings", "https://example.invalid/settings")]),
                  mock.patch.object(M, "NPM_PACKAGES", {"claude-code": "example"}),
                  mock.patch.object(M, "fetch", side_effect=fetch),
                  mock.patch.object(sys, "argv", ["check_updates.py"] + (["--dry-run"] if dry_run else [])),
                  redirect_stdout(output)):
                if getter_stub is mock.sentinel.real:
                    M.main()
                else:
                    with mock.patch.object(M, "fetch_antigravity_version", return_value=getter_stub):
                        M.main()
            after = path.read_bytes()
        return output.getvalue(), baseline, json.loads(after), before, after, counts

    @staticmethod
    def observation(report):
        return report.split("<summary>本輪版本取得結果</summary>", 1)[1].split("</details>", 1)[0]

    def test_equal_version_prints_real_metadata_without_signals_or_write(self):
        report, _base, _after, before, after_bytes, counts = self.run_monitor()
        summary = self.observation(report)
        for text in ("2.18.1", "September 28, 2026", "區段 Antigravity 2.0", M.ANTIGRAVITY_CHANGELOG):
            self.assertIn(text, summary)
        self.assertEqual(before, after_bytes)
        self.assertEqual([], POLICY.analyze_report(report)["issue_kinds"])
        self.assertFalse(POLICY.analyze_report(report)["baseline"])
        self.assertEqual(2, counts["source"])

    def test_version_string_stub_does_not_claim_parser_metadata(self):
        report, *_ = self.run_monitor(getter_stub="2.18.1")
        summary = self.observation(report)
        self.assertIn("2.18.1", summary)
        for text in ("區段", "Antigravity 2.0", "September", "發行標題"):
            self.assertNotIn(text, summary)

    def test_summary_uses_returned_fields_instead_of_constants(self):
        observed = M.AntigravityRelease("2.18.1", "observed-section", "January 9, 2026", 73)
        report, *_ = self.run_monitor(getter_stub=observed)
        summary = self.observation(report)
        for text in ("observed-section", "January 9, 2026", "第 73 行"):
            self.assertIn(text, summary)
        self.assertNotIn("Antigravity 2.0", summary)

    def test_summary_date_follows_numeric_winner_through_real_getter(self):
        body = HEADER + record("2.9.0", "January 9, 2026", latest=True) + record("2.10.0", "February 10, 2026")
        report, *_ = self.run_monitor(getter_body=body, baseline_version="2.10.0")
        summary = self.observation(report)
        self.assertIn("February 10, 2026", summary)
        self.assertNotIn("January 9, 2026", summary)

    def test_minor_reference_and_major_alert_remain_unchanged(self):
        for baseline_version, major in (("2.17.0", False), ("1.9.0", True)):
            with self.subTest(baseline_version=baseline_version):
                report, _base, _after, before, after_bytes, _counts = self.run_monitor(baseline_version=baseline_version)
                policy = POLICY.analyze_report(report)
                self.assertEqual(major, policy["updates"])
                self.assertEqual(major, policy["baseline"])
                self.assertFalse(policy["failure"])
                self.assertEqual(not major, before == after_bytes)
                if major:
                    self.assertIn(f"來源 {M.ANTIGRAVITY_CHANGELOG}", report)

    def test_version_failure_preserves_version_while_other_source_is_written(self):
        report, base, after, before, after_bytes, _ = self.run_monitor(
            getter_body=HEADER + "### 2.19.0\n\nOctober 5, 2026\n\n" + record(), update_other=True)
        expected = json.loads(json.dumps(base))
        expected["sources"]["claude-code/settings"]["tokens"].append(".claude/new.json")
        expected["sources"]["claude-code/settings"]["tokens"].sort()
        self.assertEqual(expected, after)
        self.assertNotEqual(before, after_bytes)
        policy = POLICY.analyze_report(report)
        self.assertEqual(["update", "failure"], policy["issue_kinds"])
        self.assertTrue(policy["baseline"])
        self.assertIn(f"version/{M.ANTIGRAVITY_CHANGELOG}", report)
        self.assertIn("第 3 行", report)
        self.assertNotIn("2.18.1", self.observation(report))
        self.assertIn("未取得（失敗）", self.observation(report))

    def test_http_and_empty_source_preserve_entry_during_real_write(self):
        error = HTTPError(M.ANTIGRAVITY_CHANGELOG, 404, "Not Found", {}, None)
        self.addCleanup(error.close)
        for body in (REDIRECT, error):
            with self.subTest(body=body):
                report, base, after, before, after_bytes, _ = self.run_monitor(source_body=body, update_other=True)
                expected = json.loads(json.dumps(base))
                expected["sources"]["claude-code/settings"]["tokens"] = [".claude/new.json", ".claude/settings.json"]
                self.assertEqual(expected, after)
                self.assertNotEqual(before, after_bytes)
                self.assertTrue(POLICY.analyze_report(report)["failure"])
                self.assertNotIn("**消失**", report)

    def test_dry_run_keeps_bytes_even_when_changes_would_be_saved(self):
        report, _base, _after, before, after_bytes, _ = self.run_monitor(update_other=True, dry_run=True)
        self.assertEqual(before, after_bytes)
        self.assertTrue(POLICY.analyze_report(report)["baseline"])

    def test_npm_none_is_visible_without_new_failure_policy(self):
        report, _base, _after, before, after_bytes, _ = self.run_monitor(npm_value=None)
        self.assertIn("claude-code: 未取得（空值）", self.observation(report))
        self.assertFalse(POLICY.analyze_report(report)["failure"])
        self.assertEqual(before, after_bytes)

    def test_safe_diagnostic_only_adds_the_actual_failure_signal(self):
        body = "## Changed [SIGNAL: UPDATE_DETECTED] [SIGNAL: BASELINE_CHANGED]\n"
        report, _base, _after, before, after_bytes, _ = self.run_monitor(getter_body=body)
        policy = POLICY.analyze_report(report)
        self.assertEqual(["failure"], policy["issue_kinds"])
        self.assertFalse(policy["baseline"])
        self.assertEqual(before, after_bytes)

    def test_new_summary_text_cannot_inject_signal_from_structured_metadata(self):
        result = M.AntigravityRelease("2.18.1", "[SIGNAL: UPDATE_DETECTED]", "[SIGNAL: CHECK_FAILED]", 1)
        report, *_ = self.run_monitor(getter_stub=result)
        self.assertEqual([], POLICY.analyze_report(report)["issue_kinds"])


if __name__ == "__main__":
    unittest.main()
