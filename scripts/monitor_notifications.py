#!/usr/bin/env python3
"""Deliver an update report to its repository/run issue; fail closed on ambiguity.

Failure notifications retain the existing workflow path. No new detection state
is stored in the repository. This command is only called by the live notify step.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

RULES_BEGIN = '<!-- ai-tools-monitor rules-begin -->'
RULES_END = '<!-- ai-tools-monitor rules-end -->'


def same_rules(issue, rules, fingerprint):
    """Check delivered bytes too; a surviving SHA marker alone is insufficient."""
    body = issue.get('body') or ''
    begin, end = RULES_BEGIN + '\n', '\n' + RULES_END
    if body.count(begin) != 1 or body.count(end) != 1:
        return False
    stored = body.split(begin, 1)[1].split(end, 1)[0]
    return fingerprint in body.split('\n') and stored == rules


def gh(*args, check=True):
    result = subprocess.run(['gh', *args], capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
    if check and result.returncode:
        raise RuntimeError(f'GitHub command failed ({result.returncode}): {result.stderr[:500]}')
    return result


def run_marker(repo, run_id):
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo) or not re.fullmatch(r'[0-9]+', run_id):
        raise ValueError('Invalid repository or run id')
    return f'<!-- ai-tools-monitor repository={repo} kind=update run={run_id} -->'


def find_issue(repo, marker):
    # --slurp preserves page boundaries. A query error is never an empty result.
    result = gh('api', '--paginate', '--slurp', f'repos/{repo}/issues?state=all&per_page=100')
    pages = json.loads(result.stdout)
    if not isinstance(pages, list) or not pages or any(not isinstance(p, list) for p in pages):
        raise ValueError('Invalid paginated issue response')
    matches = []
    expected_repo_url = os.environ.get('GITHUB_API_URL', 'https://api.github.com').rstrip('/') + '/repos/' + repo
    for page in pages:
        for issue in page:
            if not isinstance(issue, dict):
                raise ValueError('Invalid issue response')
            if 'pull_request' in issue or marker not in (issue.get('body') or '').splitlines():
                continue
            if (issue.get('repository_url') != expected_repo_url or
                    type(issue.get('number')) is not int or issue['number'] <= 0 or
                    issue.get('state') not in ('open', 'closed')):
                raise ValueError('Invalid run issue identity')
            matches.append(issue)
    if len(matches) > 1:
        raise ValueError('Multiple issues have the same repository/run identity')
    return matches[0] if matches else None


def deliver(repo, run_id, owner, report, rules):
    marker = run_marker(repo, run_id)
    digest = hashlib.sha256(rules.encode('utf-8')).hexdigest()
    fingerprint = f'<!-- ai-tools-monitor rules-sha256={digest} -->'
    if not rules or report.count(rules) != 1 or RULES_BEGIN in report or RULES_END in report:
        raise ValueError('Display report must contain exactly one unambiguous rules report')
    display = report.replace(rules, RULES_BEGIN + '\n' + rules + '\n' + RULES_END, 1)
    body = marker + '\n' + fingerprint + '\n\n' + display
    issue = find_issue(repo, marker)
    with tempfile.TemporaryDirectory(prefix='monitor-notify-') as directory:
        body_file = Path(directory) / 'body.md'
        body_file.write_text(body, encoding='utf-8', newline='\n')
        if issue is None:
            # A failed/malformed response may hide a successful create. Never retry
            # creation blindly; recover only by looking up the same stable identity.
            gh('issue', 'create', '--repo', repo,
               '--title', f'🚨 偵測到 AI 工具路徑與機制異動 · run {run_id}',
               '--body-file', str(body_file), '--assignee', owner, check=False)
            for _attempt in range(3):
                issue = find_issue(repo, marker)
                if issue is not None:
                    break
            if issue is None:
                raise RuntimeError('Create outcome unconfirmed; inspect this run before retrying')
        if same_rules(issue, rules, fingerprint):
            print(f'Update delivered to #{issue["number"]}; identical rules report')
            return
        if issue['state'] == 'closed':
            raise RuntimeError(f'Run issue #{issue["number"]} is closed with different content; manual review required')
        gh('issue', 'edit', str(issue['number']), '--repo', repo, '--body-file', str(body_file))
        verified = find_issue(repo, marker)
        if (verified is None or verified['number'] != issue['number'] or
                verified['state'] != 'open' or not same_rules(verified, rules, fingerprint)):
            raise RuntimeError('Updated delivery unconfirmed or issue closed during update; manual review required')
        print(f'Updated run issue #{issue["number"]}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--rules', required=True)
    args = parser.parse_args(argv)
    deliver(args.repo, args.run_id, args.owner,
            Path(args.report).read_text(encoding='utf-8'),
            Path(args.rules).read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
