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
import sys
import tempfile
import time
from pathlib import Path

RULES_BEGIN = '<!-- ai-tools-monitor rules-begin -->'
RULES_END = '<!-- ai-tools-monitor rules-end -->'
# Five reads, with at most 15 seconds of deliberate waiting per confirmation.
READ_BACKOFF = (1, 2, 4, 8)


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


def retry_read(read, description, accept=lambda issue: issue is not None):
    """Retry missing/stale reads and command failures, never malformed identities.

    A final query error is raised, not converted into an empty list that could
    authorize creation. Writes are never retried by this helper.
    """
    for attempt in range(len(READ_BACKOFF) + 1):
        try:
            result = read()
        except RuntimeError:
            if attempt == len(READ_BACKOFF):
                raise
        else:
            if accept(result) or attempt == len(READ_BACKOFF):
                return result
        delay = READ_BACKOFF[attempt]
        print(f'{description} not confirmed; retrying in {delay}s', file=sys.stderr)
        time.sleep(delay)


def validate_issue(issue, repo, number=None):
    expected_repo_url = os.environ.get('GITHUB_API_URL', 'https://api.github.com').rstrip('/') + '/repos/' + repo
    if (not isinstance(issue, dict) or 'pull_request' in issue or
            issue.get('repository_url') != expected_repo_url or
            type(issue.get('number')) is not int or issue['number'] <= 0 or
            (number is not None and issue['number'] != number) or
            issue.get('state') not in ('open', 'closed') or
            not isinstance(issue.get('body'), (str, type(None)))):
        raise ValueError('Invalid run issue identity')


def find_issue(repo, marker):
    # --slurp preserves page boundaries. A query error is never an empty result.
    result = gh('api', '--paginate', '--slurp', f'repos/{repo}/issues?state=all&per_page=100')
    pages = json.loads(result.stdout)
    if not isinstance(pages, list) or not pages or any(not isinstance(p, list) for p in pages):
        raise ValueError('Invalid paginated issue response')
    matches = []
    for page in pages:
        for issue in page:
            if not isinstance(issue, dict):
                raise ValueError('Invalid issue response')
            if 'pull_request' in issue or marker not in (issue.get('body') or '').splitlines():
                continue
            validate_issue(issue, repo)
            matches.append(issue)
    if len(matches) > 1:
        raise ValueError('Multiple issues have the same repository/run identity')
    return matches[0] if matches else None


def created_issue_number(output, repo):
    # gh issue create prints an issue URL. Treat it only as a hint, constrained
    # to this server/repository; a direct API read must still prove the identity.
    server = os.environ.get('GITHUB_SERVER_URL', 'https://github.com').rstrip('/')
    pattern = re.compile(re.escape(f'{server}/{repo}/issues/') + r'([1-9][0-9]*)')
    numbers = [int(match[1]) for line in output.splitlines()
               if (match := pattern.fullmatch(line.strip()))]
    return numbers[0] if len(numbers) == 1 else None


def get_issue(repo, number, marker):
    issue = json.loads(gh('api', f'repos/{repo}/issues/{number}').stdout)
    validate_issue(issue, repo, number)
    return issue if marker in (issue.get('body') or '').splitlines() else None


def deliver(repo, run_id, owner, report, rules):
    marker = run_marker(repo, run_id)
    digest = hashlib.sha256(rules.encode('utf-8')).hexdigest()
    fingerprint = f'<!-- ai-tools-monitor rules-sha256={digest} -->'
    if not rules or report.count(rules) != 1 or RULES_BEGIN in report or RULES_END in report:
        raise ValueError('Display report must contain exactly one unambiguous rules report')
    display = report.replace(rules, RULES_BEGIN + '\n' + rules + '\n' + RULES_END, 1)
    body = marker + '\n' + fingerprint + '\n\n' + display
    issue = retry_read(lambda: find_issue(repo, marker), 'Run issue lookup')
    with tempfile.TemporaryDirectory(prefix='monitor-notify-') as directory:
        body_file = Path(directory) / 'body.md'
        body_file.write_text(body, encoding='utf-8', newline='\n')
        if issue is None:
            # Create at most once. Bypass the eventually consistent list when gh
            # supplies a usable issue URL, even if its exit status is nonzero.
            created = gh('issue', 'create', '--repo', repo,
               '--title', f'🚨 偵測到 AI 工具路徑與機制異動 · run {run_id}',
               '--body-file', str(body_file), '--assignee', owner, check=False)
            number = created_issue_number(created.stdout, repo)
            read = (lambda: get_issue(repo, number, marker)) if number is not None else (
                lambda: find_issue(repo, marker))
            issue = retry_read(read, 'Created issue lookup')
            if issue is None:
                raise RuntimeError('Create outcome unconfirmed; inspect this run before retrying')
        if same_rules(issue, rules, fingerprint):
            print(f'Update delivered to #{issue["number"]}; identical rules report')
            return
        if issue['state'] == 'closed':
            raise RuntimeError(f'Run issue #{issue["number"]} is closed with different content; manual review required')
        gh('issue', 'edit', str(issue['number']), '--repo', repo, '--body-file', str(body_file))
        verified = retry_read(lambda: get_issue(repo, issue['number'], marker),
                              'Edited issue confirmation',
                              accept=lambda current: current is not None and (
                                  current['state'] == 'closed' or same_rules(current, rules, fingerprint)))
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
