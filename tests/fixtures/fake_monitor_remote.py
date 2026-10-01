"""Filesystem-only gh/git substitute; never delegates to a real executable."""
import json
import os
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
op = args[2] if args[1] == 'issue' else 'list'
failure = os.environ.get('FAIL_OP', '')
if failure == op:
    sys.exit(2)
writes = [c for c in calls if c[:2] == ['gh','issue'] and c[2] in ('create','comment','edit')]
if failure == 'second' and op in ('create','comment','edit') and len(writes) == 2:
    sys.exit(2)
if args[1] == 'api':
    issues = state['issues']
    print(json.dumps([issues[:1], issues[1:]]))
elif op == 'list':
    print(json.dumps([i for i in state['issues'] if i['state'].lower() == 'open']))
elif op in ('create','edit'):
    body = Path(args[args.index('--body-file') + 1]).read_text(encoding='utf-8')
    if op == 'create':
        number = 100 + len(state['issues'])
        state['issues'].append({'number':number, 'title':args[args.index('--title')+1],
            'body':body, 'state':'open', 'repository_url':'https://api.github.com/repos/test/repo'})
        if state.get('close_legacy_after_create'):
            for issue in state['issues']:
                if issue['number'] == 15:
                    issue['state'] = 'closed'
    else:
        number = int(args[3])
        issue = next(i for i in state['issues'] if i['number'] == number)
        issue['body'] = body
        if state.get('close_during_edit'):
            issue['state'] = 'closed'
    state_path.write_text(json.dumps(state))
    if op == 'create' and state.get('lose_create_response'):
        sys.exit(2)
    print(f'https://github.com/test/repo/issues/{number}')
