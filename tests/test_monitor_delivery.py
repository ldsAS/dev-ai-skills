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


FAKE = r'''
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
path = Path('calls.json')
calls = json.loads(path.read_text()) if path.exists() else []
calls.append(args)
path.write_text(json.dumps(calls))
kind = args[0]
if kind == 'git':
    sys.exit(1 if args[1:3] == ['diff', '--quiet'] else 0)
op = args[2]
if op == os.environ.get('FAIL_OP'):
    sys.exit(2)
if os.environ.get('FAIL_OP') == 'second' and op in ('create', 'comment'):
    if sum(c[:3] in (['gh','issue','create'], ['gh','issue','comment']) for c in calls) == 2:
        sys.exit(2)
if op == 'list':
    print(json.dumps(json.loads(os.environ['ISSUES'])))
elif op == 'create':
    print('https://github.com/test/repo/issues/100')
'''


class DeliveryTests(unittest.TestCase):
    def run_delivery(self, issues=(), fail_op='', kinds='update failure', mode='false'):
        bash = 'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash')
        if not bash:
            self.skipTest('Bash required')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            (root / 'fake.py').write_text(FAKE, encoding='utf-8')
            (root / 'report.md').write_text('report\n', encoding='utf-8')
            python = shlex.quote(Path(sys.executable).as_posix())
            env = dict(os.environ, OWNER='test', RUN_URL='https://github.com/test/repo/actions/runs/123',
                       ISSUE_KINDS=kinds, ISSUES=json.dumps(issues), FAIL_OP=fail_op)
            values = {'steps.mode.outputs.dry_run':mode, 'steps.check.outcome':'success',
                      'steps.check.outputs.updates':str('update' in kinds).lower(),
                      'steps.check.outputs.failure':str('failure' in kinds).lower(),
                      'steps.check.outputs.baseline':'true'}
            def execute(name):
                shell = STEPS[name]['run'].replace('python scripts/', python + ' scripts/')
                shell = shell.replace('gh ', python + ' fake.py gh ').replace('git ', python + ' fake.py git ')
                return subprocess.run([bash, '-e', '-o', 'pipefail', '-c', shell], cwd=root, env=env,
                                      capture_output=True, encoding='utf-8', errors='replace')
            notify = None
            if allows('Notify via GitHub Issues', values):
                notify = execute('Notify via GitHub Issues')
            values['steps.notify.outcome'] = 'skipped' if notify is None else ('success' if notify.returncode == 0 else 'failure')
            if allows('Commit baseline update', values):
                result = execute('Commit baseline update')
                self.assertEqual(0, result.returncode, result.stderr)
            calls = json.loads((root / 'calls.json').read_text()) if (root / 'calls.json').exists() else []
            return calls, notify

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
            issues = [{'number':15,'title':'🚨 偵測到 AI 工具路徑與機制異動','state':'OPEN'}] if fail == 'comment' else []
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
