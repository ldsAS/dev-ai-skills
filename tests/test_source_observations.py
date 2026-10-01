import html
import json
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

import test_antigravity_changelog as changelog
from test_antigravity_changelog import FIXTURE, HEADER, M, POLICY, ROOT, record


class SourceObservationTests(unittest.TestCase):
    run_monitor = changelog.ChangelogIntegrationTests.run_monitor

    def test_path_and_version_share_one_body_even_if_next_fetch_would_differ(self):
        for second in (FIXTURE.replace('2.18.1','3.0.0'), OSError('second request')):
            report, _, _, before, after, counts = self.run_monitor(getter_body=second)
            self.assertEqual(1, counts['source'])
            self.assertEqual([], POLICY.analyze_report(report)['issue_kinds'])
            self.assertEqual(before, after)
            self.assertNotIn('3.0.0', report)

    def test_parser_receives_raw_while_tokens_receive_normalized_body(self):
        raw = FIXTURE + '\nEscaped path \\u002eagents/demo.json\n'
        original = M.parse_antigravity_changelog
        with mock.patch.object(M, 'parse_antigravity_changelog', wraps=original) as parser:
            report, _, after, *_ = self.run_monitor(source_body=raw)
        parser.assert_called_once_with(raw)
        self.assertIn('.agents/demo.json', after['sources']['antigravity/changelog']['tokens'])

    def test_three_transport_attempts_not_six_and_next_main_never_reuses_success(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = FIXTURE.encode()
        response.headers = {}
        baseline = {'schema':2,'versions':{'antigravity':'2.18.1'},'sources':{
            'antigravity/changelog':{'tokens':sorted(M.extract_tokens(M.normalize(FIXTURE)))}}}
        with (mock.patch.object(M,'SOURCES',[('antigravity','changelog',M.ANTIGRAVITY_CHANGELOG)]),
              mock.patch.object(M,'NPM_PACKAGES',{}), mock.patch.object(M,'load_baseline',return_value=baseline),
              mock.patch.object(M.urllib.request,'urlopen',side_effect=[response,OSError('offline'),OSError('offline'),OSError('offline')]) as fetch,
              mock.patch.object(M.time,'sleep'), mock.patch.object(sys,'argv',['check_updates.py','--dry-run'])):
            first, second = StringIO(), StringIO()
            with redirect_stdout(first): M.main()
            with redirect_stdout(second): M.main()
        self.assertEqual(4, fetch.call_count)
        self.assertFalse(POLICY.analyze_report(first.getvalue())['failure'])
        self.assertTrue(POLICY.analyze_report(second.getvalue())['failure'])
        self.assertIn('antigravity/changelog', second.getvalue())
        self.assertIn('version/'+M.ANTIGRAVITY_CHANGELOG, second.getvalue())
        self.assertIn('未取得（失敗）', second.getvalue())
        self.assertNotIn('September 28', second.getvalue())

    def test_valid_product_with_zero_tokens_preserves_source_but_reports_real_major(self):
        report, before, after, *_ = self.run_monitor(source_body=HEADER+record('3.0.0'))
        self.assertEqual(before['sources'],after['sources'])
        self.assertEqual('3.0.0', after['versions']['antigravity'])
        self.assertEqual(['update','failure'],POLICY.analyze_report(report)['issue_kinds'])

    def test_bad_parser_does_not_discard_successful_new_tokens(self):
        body = FIXTURE.replace('### [v2.18.1]', '### [2.18.1]') + '\n.agents/new.json\n'
        report, before, after, *_ = self.run_monitor(source_body=body)
        self.assertEqual(before['versions'], after['versions'])
        self.assertIn('.agents/new.json', after['sources']['antigravity/changelog']['tokens'])
        self.assertEqual(['update','failure'], POLICY.analyze_report(report)['issue_kinds'])

    def test_historical_redirect_targets_are_visible_with_no_extra_fetch_or_token_loss(self):
        for filename, target in [('antigravity-changelog-redirect.html','/docs/changelog'),
                                 ('antigravity-ide-skills-redirect.html','/docs/skills?tab=ide'),
                                 ('antigravity-rules-redirect.html','/docs/rules')]:
            raw = (ROOT/'tests/fixtures'/filename).read_text(encoding='utf-8')
            report, base, after, before_bytes, after_bytes, counts = self.run_monitor(source_body=raw)
            self.assertEqual(1, counts['source'])
            self.assertEqual(before_bytes, after_bytes)
            self.assertEqual(base,after)
            self.assertIn('文件宣告的導向目標',report)
            self.assertIn('https://antigravity.google'+target,html.unescape(report))
            self.assertTrue(POLICY.analyze_report(report)['failure'])

    def test_meta_attributes_ambiguity_invalid_and_unsafe_targets(self):
        fixtures = [
            ('''<html><META CONTENT=" 0 ; URL = '../target?q=one&amp;x=two' " HTTP-EQUIV=' Refresh '></html>''', 'https://antigravity.google/target?q=one&x=two'),
            ('''<html><meta http-equiv='refresh' content='0;url=/one'><meta content='0;url=/two' http-equiv='refresh'></html>''', '歧義'),
            ('''<html><meta http-equiv='refresh' content='0;url=javascript:alert(1)'></html>''','無效／不安全'),
            ('''<html><meta http-equiv='refresh'></html>''','無效／不安全'),
            ('''<html><meta http-equiv='refresh' content='nonsense'></html>''','無效／不安全'),
            ('''<html><meta http-equiv='refresh' content='0;url=//[bad'></html>''','無效／不安全'),
            ('''<html><meta http-equiv='refresh' content='0;url=/one' content='0;url=/two'></html>''','屬性重複'),
        ]
        for body, expected in fixtures:
            with self.subTest(body=body):
                report, _, _, before, after, counts = self.run_monitor(source_body=body)
                self.assertIn(expected,html.unescape(report))
                self.assertEqual(before,after)
                self.assertEqual(1,counts['source'])
                self.assertTrue(POLICY.analyze_report(report)['failure'])

    def test_meta_does_not_change_empty_token_threshold_or_follow_url(self):
        body = FIXTURE + "\n<html><meta http-equiv='refresh' content='0;url=https://example.invalid'></html>"
        report, _, _, before, after, counts = self.run_monitor(source_body=body)
        self.assertEqual([], POLICY.analyze_report(report)['issue_kinds'])
        self.assertNotIn('文件宣告的導向目標',report)
        self.assertEqual(before,after)
        self.assertEqual(1,counts['source'])

    def test_line_numbers_use_lf_not_unicode_separators_and_accept_crlf(self):
        for separator in ('\u0085','\u2028','\u2029'):
            for newline in ('\n','\r\n'):
                body=('paragraph'+separator+'continuation\n'+HEADER+'### 2.19.0\n\nOctober 5, 2026\n'+record()).replace('\n',newline)
                with self.assertRaises(ValueError) as raised: M.parse_antigravity_changelog(body)
                self.assertIn('第 4 行',str(raised.exception))
                self.assertIn('### 2.19.0',str(raised.exception))
