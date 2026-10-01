"""External report text must remain display data through the real main()."""
import html
import runpy
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

import test_antigravity_changelog as changelog
from test_antigravity_changelog import FIXTURE, M, POLICY
from test_monitor_workflow import ROOT


class ReportBoundaryTests(unittest.TestCase):
    run_monitor = changelog.ChangelogIntegrationTests.run_monitor

    def test_npm_new_and_old_versions_cannot_create_signals(self):
        for marker in (POLICY.UPDATE_SIGNAL, POLICY.FAILURE_SIGNAL, POLICY.BASELINE_SIGNAL):
            with self.subTest(marker=marker):
                value = "1.0.1\n" + marker + "\n"
                report, *_ = self.run_monitor(npm_value=value)
                self.assertEqual([], POLICY.analyze_report(report)["issue_kinds"])
                self.assertFalse(POLICY.analyze_report(report)["baseline"])
                with mock.patch.object(M, "load_baseline", return_value={
                    "schema": 2, "sources": {}, "versions": {"claude-code": value}}):
                    report, *_ = self.run_monitor(dry_run=True)
                self.assertEqual([], POLICY.analyze_report(report)["issue_kinds"])
                self.assertIn(M.report_text(value), report)

    def test_exception_cannot_add_update_or_baseline(self):
        for marker in (POLICY.UPDATE_SIGNAL, POLICY.BASELINE_SIGNAL):
            report, _, _, before, after, _ = self.run_monitor(source_body=OSError("\n" + marker + "\n"))
            self.assertEqual(["failure"], POLICY.analyze_report(report)["issue_kinds"])
            self.assertFalse(POLICY.analyze_report(report)["baseline"])
            self.assertEqual(before, after)
            self.assertNotIn("\n" + marker + "\n", report)

    def test_full_context_tail_survives_safety_cleanup_in_main(self):
        body = FIXTURE + "\n" + "a" * 115 + " .claude/installed_plugins.unreadable " + "b" * 60 + " [SIGNAL: CHECK_FAILED] Nothing reads them."
        token = ".claude/installed_plugins.unreadable"
        context = M.context_for(body, token)
        self.assertGreater(len(context), 240)
        report, *_ = self.run_monitor(source_body=body)
        excerpt = next(line[4:] for line in report.split("\n") if line.startswith("  > ") and "Nothing reads" in line)
        self.assertEqual(context, html.unescape(excerpt))
        self.assertNotIn("已截斷", excerpt)
        self.assertNotIn(POLICY.FAILURE_SIGNAL, excerpt)
        self.assertFalse(POLICY.analyze_report(report)["failure"])

    def test_short_excerpt_and_diagnostic_limit(self):
        self.assertEqual(".claude/demo/", M.report_text(".claude/demo/", limit=None))
        self.assertIn("已截斷", M.report_text("x" * 241))
        self.assertEqual("x" * 241, M.report_text("x" * 241, limit=None))

    def test_unexpected_traceback_is_prefixed_and_only_sets_failure(self):
        output = StringIO()
        with mock.patch('argparse.ArgumentParser.parse_args', side_effect=RuntimeError(
            '\n[SIGNAL: UPDATE_DETECTED]\n[SIGNAL: BASELINE_CHANGED]\n')):
            with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
                runpy.run_path(str(ROOT / 'scripts/check_updates.py'), run_name='__main__')
        self.assertEqual(1, raised.exception.code)
        self.assertEqual(['failure'], POLICY.analyze_report(output.getvalue())['issue_kinds'])
        self.assertFalse(POLICY.analyze_report(output.getvalue())['baseline'])
