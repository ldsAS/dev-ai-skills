"""Run the actual notification/commit shells in a temporary fake remote."""
import itertools
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_monitor_workflow import ROOT, STEPS, allows




class DeliveryTests(unittest.TestCase):
    def run_delivery(self, issues=(), fail_op='', kinds='update failure', mode='false', *,
                     attempts=None, remote_options=None):
        bash = 'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash')
        if not bash:
            self.skipTest('Bash required')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copyfile(ROOT / 'tests/fixtures/fake_monitor_remote.py', root / 'fake.py')
            (root / 'remote.json').write_text(json.dumps(dict(issues=list(issues), **(remote_options or {}))))
            # Route the real Python notification command's gh calls to the same
            # fake used by the shell, including on Windows without a .cmd shim.
            (root / 'sitecustomize.py').write_text(
                'import subprocess, sys\n_original = subprocess.run\n'
                'def _run(args, *a, **kw):\n'
                '    if args[0] == "gh": args = [sys.executable, "fake.py", *args]\n'
                '    return _original(args, *a, **kw)\n'
                'subprocess.run = _run\n', encoding='utf-8')
            python = shlex.quote(Path(sys.executable).as_posix())
            env = dict(os.environ, OWNER='test', RUN_URL='https://github.com/test/repo/actions/runs/123',
                       ISSUE_KINDS=kinds, FAIL_OP=fail_op, PYTHONPATH=str(root),
                       REPOSITORY='test/repo', RUN_ID='123', GITHUB_API_URL='https://api.github.com')
            values = {'steps.mode.outputs.dry_run':mode, 'steps.check.outcome':'success',
                      'steps.check.outputs.updates':str('update' in kinds).lower(),
                      'steps.check.outputs.failure':str('failure' in kinds).lower(),
                      'steps.check.outputs.baseline':'true'}
            def execute(name):
                shell = STEPS[name]['run'].replace('python scripts/', python + ' scripts/')
                shell = shell.replace('gh ', python + ' fake.py gh ').replace('git ', python + ' fake.py git ')
                return subprocess.run([bash, '-e', '-o', 'pipefail', '-c', shell], cwd=root, env=env,
                                      capture_output=True, encoding='utf-8', errors='replace')
            outcomes = []
            for attempt in (attempts or [{}]):
                env.update(RUN_ID=attempt.get('run','123'), GITHUB_RUN_ATTEMPT=attempt.get('attempt','1'))
                rules = attempt.get('rules','report\n')
                (root / 'report.md').write_text(attempt.get('display','AI summary\n') + '\n' + rules, encoding='utf-8')
                (root / 'report-rules.md').write_text(rules, encoding='utf-8')
                state = json.loads((root/'remote.json').read_text())
                if attempt.get('close'):
                    for issue in state['issues']: issue['state'] = 'closed'
                    (root/'remote.json').write_text(json.dumps(state))
                if attempt.get('corrupt_body'):
                    for issue in state['issues']:
                        issue['body'] = issue.get('body','').replace('rules-begin -->\nreport', 'rules-begin -->\nerased')
                    (root/'remote.json').write_text(json.dumps(state))
                notify = execute('Notify via GitHub Issues') if allows('Notify via GitHub Issues', values) else None
                values['steps.notify.outcome'] = 'skipped' if notify is None else ('success' if notify.returncode == 0 else 'failure')
                committed = allows('Commit baseline update', values)
                if committed:
                    result = execute('Commit baseline update')
                    self.assertEqual(0, result.returncode, result.stderr)
                outcomes.append((notify, committed))
            calls = json.loads((root / 'calls.json').read_text()) if (root / 'calls.json').exists() else []
            self.remote = json.loads((root/'remote.json').read_text())
            self.outcomes = outcomes
            return calls, outcomes[-1][0]

    def test_notify_outcome_matrix_on_real_guard(self):
        self.assertEqual('notify', STEPS['Notify via GitHub Issues']['id'])
        for mode, check, updates, failure, notify, baseline in itertools.product(
            ('false','true',''), ('success','failure','cancelled','skipped',''),
            ('true','false'), ('true','false'), ('success','failure','cancelled','skipped',''), ('true','false')):
            values = {'steps.mode.outputs.dry_run':mode, 'steps.check.outcome':check,
                      'steps.check.outputs.updates':updates, 'steps.check.outputs.failure':failure,
                      'steps.notify.outcome':notify, 'steps.check.outputs.baseline':baseline}
            expected = mode == 'false' and check == 'success' and baseline == 'true' and (
                updates == failure == 'false' or notify == 'success')
            self.assertEqual(expected, allows('Commit baseline update', values), values)

    def test_list_create_comment_and_partial_delivery_fail_closed(self):
        for fail in ('list','create','comment','second'):
            issues = [{'number':20,'title':'⚠️ AI 工具異動檢查失敗','state':'open'}] if fail == 'comment' else []
            with self.subTest(fail=fail):
                calls, result = self.run_delivery(issues, fail)
                self.assertNotEqual(0, result.returncode)
                self.assertFalse(any(c[0] == 'git' for c in calls), calls)

    def test_success_and_no_notification_bootstrap_can_commit(self):
        for kinds in ('update failure',''):
            calls, _ = self.run_delivery(kinds=kinds)
            self.assertIn(['git','push'], calls)

    def test_dry_run_has_no_remote_writes(self):
        calls, _ = self.run_delivery(mode='true')
        self.assertEqual([], calls)

    def test_new_run_never_reuses_legacy_or_manual_title_even_if_closed(self):
        for state in ('open','closed'):
            legacy = {'number':15,'title':'🚨 偵測到 AI 工具路徑與機制異動','state':state,'body':'old report',
                      'repository_url':'https://api.github.com/repos/test/repo'}
            calls, result = self.run_delivery([legacy], kinds='update', remote_options={'close_legacy_after_create':True})
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(2, len(self.remote['issues']))
            self.assertFalse(any(c[:3] == ['gh','issue','comment'] for c in calls))
            self.assertEqual('old report', self.remote['issues'][0]['body'])

    def test_run_attempt_reuses_one_issue_but_next_run_is_distinct(self):
        calls, result = self.run_delivery(kinds='update', attempts=[{},
            {'attempt':'2','display':'a different AI summary and timestamp'}, {'run':'124'}])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(2, len(self.remote['issues']))
        self.assertEqual(2, sum(c[:3] == ['gh','issue','create'] for c in calls))
        self.assertFalse(any(c[:3] == ['gh','issue','edit'] for c in calls))
        self.assertTrue(all(committed for _,committed in self.outcomes))

    def test_open_different_report_updates_that_run(self):
        calls, result = self.run_delivery(kinds='update', attempts=[{}, {'rules':'new rules','display':'new report'}])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(1, len(self.remote['issues']))
        self.assertIn('new report', self.remote['issues'][0]['body'])
        self.assertEqual(1, sum(c[:3] == ['gh','issue','edit'] for c in calls))

    def test_closed_same_report_is_delivered_but_changed_report_blocks_baseline(self):
        for changed in (False, True):
            calls, result = self.run_delivery(kinds='update', attempts=[{},
                {'close':True,'rules':'different' if changed else 'report\n'}])
            self.assertEqual(not changed, self.outcomes[-1][1])
            self.assertEqual(not changed, result.returncode == 0, result.stderr)
            self.assertFalse(any(c[:3] == ['gh','issue','edit'] for c in calls))

    def test_create_lost_response_is_recovered_without_duplicate(self):
        calls, result = self.run_delivery(kinds='update', remote_options={'lose_create_response':True})
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(1, len(self.remote['issues']))
        self.assertEqual(1, sum(c[:3] == ['gh','issue','create'] for c in calls))
        self.assertIn(['git','push'], calls)

    def test_pagination_ignores_failure_marker_and_reuses_second_page(self):
        failure = {'number':20,'title':'failure','state':'open',
                   'body':'<!-- ai-tools-monitor repository=test/repo kind=failure run=123 -->'}
        calls, result = self.run_delivery([failure], kinds='update', attempts=[{}, {'attempt':'2'}])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(2, len(self.remote['issues']))
        self.assertEqual(1, sum(c[:3] == ['gh','issue','create'] for c in calls))
        self.assertTrue(all('--paginate' in c and '--slurp' in c for c in calls if c[:2] == ['gh','api']))

    def test_multiple_or_wrong_repository_identity_blocks_commit(self):
        marker = '<!-- ai-tools-monitor repository=test/repo kind=update run=123 -->'
        issue = {'number':1,'title':'arbitrary','state':'open','body':marker,
                 'repository_url':'https://api.github.com/repos/test/repo'}
        for issues in ([issue, dict(issue,number=2)], [dict(issue, repository_url='https://api.github.com/repos/other/repo')]):
            calls, result = self.run_delivery(issues, kinds='update')
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(any(c[0] == 'git' for c in calls))
            self.assertFalse(any(c[:3] == ['gh','issue','create'] for c in calls))

    def test_closed_during_edit_blocks_commit(self):
        _, result = self.run_delivery(kinds='update', attempts=[{}, {'rules':'changed'}],
                                      remote_options={'close_during_edit':True})
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.outcomes[-1][1])

    def test_query_error_never_creates_issue(self):
        calls, result = self.run_delivery(kinds='update', fail_op='list')
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(any(c[:3] == ['gh','issue','create'] or c[0] == 'git' for c in calls))

    def test_sha_marker_alone_does_not_prove_same_delivered_content(self):
        for closed in (False, True):
            calls, result = self.run_delivery(kinds='update', attempts=[{}, {'corrupt_body':True,'close':closed}])
            self.assertEqual(not closed, self.outcomes[-1][1])
            self.assertEqual(not closed, result.returncode == 0, result.stderr)
            self.assertEqual(not closed, any(c[:3] == ['gh','issue','edit'] for c in calls))
