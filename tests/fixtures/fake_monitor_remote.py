"""Filesystem-only gh/git substitute; never delegates to a real executable."""
import json
import os
import re
import sys
from pathlib import Path

args = sys.argv[1:]
calls_path, state_path = Path('calls.json'), Path('remote.json')
calls = json.loads(calls_path.read_text()) if calls_path.exists() else []
calls.append(args)
calls_path.write_text(json.dumps(calls))
state = json.loads(state_path.read_text())
kind = args[0]
if kind == 'git':
    sys.exit(1 if args[1:3] == ['diff', '--quiet'] else 0)
direct = re.fullmatch(r'repos/test/repo/issues/([0-9]+)', args[-1]) if args[1] == 'api' else None
op = args[2] if args[1] == 'issue' else ('get' if direct else 'list')
failure = os.environ.get('FAIL_OP', '')
if failure == op:
    sys.exit(2)
writes = [c for c in calls if c[:2] == ['gh','issue'] and c[2] in ('create','comment','edit')]
if failure == 'second' and op in ('create','comment','edit') and len(writes) == 2:
    sys.exit(2)
if args[1] == 'api':
    if direct:
        if state.get('get_missing_remaining', 0):
            state['get_missing_remaining'] -= 1
            state_path.write_text(json.dumps(state))
            sys.exit(2)
        issue = next(i for i in state['issues'] if i['number'] == int(direct[1]))
        if state.get('get_stale_remaining', 0):
            state['get_stale_remaining'] -= 1
            issue = state['stale_issue']
        issue = dict(issue, **state.get('direct_overrides', {}))
        state_path.write_text(json.dumps(state))
        print(json.dumps(issue))
    else:
        if state.get('list_error_remaining', 0):
            state['list_error_remaining'] -= 1
            state_path.write_text(json.dumps(state))
            sys.exit(2)
        issues = state['issues']
        if state.get('list_hidden_remaining', 0):
            state['list_hidden_remaining'] -= 1
            issues = [i for i in issues if 'kind=update' not in (i.get('body') or '')]
        if state.get('list_stale_remaining', 0):
            state['list_stale_remaining'] -= 1
            issues = [state['stale_issue'] if i['number'] == state['stale_issue']['number'] else i
                      for i in issues]
        state_path.write_text(json.dumps(state))
        print(json.dumps([issues[:1], issues[1:]]))
elif op == 'list':
    print(json.dumps([i for i in state['issues'] if i['state'].lower() == 'open']))
elif op in ('create','edit'):
    body = Path(args[args.index('--body-file') + 1]).read_text(encoding='utf-8')
    if op == 'create':
        number = 100 + len(state['issues'])
        state['issues'].append({'number':number, 'title':args[args.index('--title')+1],
            'body':body, 'state':'open', 'repository_url':'https://api.github.com/repos/test/repo'})
        state['list_hidden_remaining'] = state.get('create_list_delay', 0)
        state['get_missing_remaining'] = state.get('create_direct_delay', 0)
        if state.get('close_legacy_after_create'):
            for issue in state['issues']:
                if issue['number'] == 15:
                    issue['state'] = 'closed'
    else:
        number = int(args[3])
        issue = next(i for i in state['issues'] if i['number'] == number)
        state['stale_issue'] = dict(issue)
        state['get_stale_remaining'] = state.get('edit_direct_delay', 0)
        state['list_stale_remaining'] = state.get('edit_list_delay', 0)
        issue['body'] = body
        if state.get('close_during_edit'):
            issue['state'] = 'closed'
    state_path.write_text(json.dumps(state))
    if op == 'create' and state.get('lose_create_response'):
        sys.exit(2)
    print(state.get('create_output', f'https://github.com/test/repo/issues/{number}')
          if op == 'create' else f'https://github.com/test/repo/issues/{number}')
