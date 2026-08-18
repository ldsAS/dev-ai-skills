#!/usr/bin/env python3
"""Pure policy helpers for the AI-tool update monitor workflow.

This module deliberately has no GitHub side effects.  It converts a monitor
report into stable workflow outputs and selects exact-title recovery targets
from issue JSON supplied by the workflow.
"""

import argparse
import json
import sys
from pathlib import Path


UPDATE_SIGNAL = "[SIGNAL: UPDATE_DETECTED]"
FAILURE_SIGNAL = "[SIGNAL: CHECK_FAILED]"
BASELINE_SIGNAL = "[SIGNAL: BASELINE_CHANGED]"


for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")


def analyze_report(report_text, exit_code=0):
    """Return workflow decisions derived from report signals and exit status."""
    updates = UPDATE_SIGNAL in report_text
    failure = FAILURE_SIGNAL in report_text or exit_code != 0
    baseline = BASELINE_SIGNAL in report_text
    issue_kinds = []
    if updates:
        issue_kinds.append("update")
    if failure:
        issue_kinds.append("failure")
    return {
        "updates": updates,
        "failure": failure,
        "baseline": baseline,
        "should_fail": failure,
        "issue_kinds": issue_kinds,
    }


def recovery_targets(issues, title):
    """Return every open issue number whose title is an exact match."""
    return [
        issue["number"]
        for issue in issues
        if issue.get("state", "OPEN").upper() == "OPEN"
        and issue.get("title") == title
        and isinstance(issue.get("number"), int)
    ]


def _github_bool(value):
    return "true" if value else "false"


def write_github_outputs(path, decisions):
    """Append scalar policy decisions to a GitHub Actions output file."""
    values = {
        "updates": _github_bool(decisions["updates"]),
        "failure": _github_bool(decisions["failure"]),
        "baseline": _github_bool(decisions["baseline"]),
        "should_fail": _github_bool(decisions["should_fail"]),
        "issue_kinds": " ".join(decisions["issue_kinds"]),
    }
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def _analyze(args):
    report_text = Path(args.report).read_text(encoding="utf-8")
    decisions = analyze_report(report_text, args.exit_code)
    if args.github_output:
        write_github_outputs(args.github_output, decisions)
    print(json.dumps(decisions, ensure_ascii=False, sort_keys=True))
    return 0


def _targets(args):
    issues = json.loads(Path(args.issues).read_text(encoding="utf-8"))
    for number in recovery_targets(issues, args.title):
        print(number)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="解析報告與 exit code")
    analyze_parser.add_argument("--report", required=True)
    analyze_parser.add_argument("--exit-code", type=int, default=0)
    analyze_parser.add_argument("--github-output")
    analyze_parser.set_defaults(handler=_analyze)

    targets_parser = subparsers.add_parser("targets", help="列出完全同標題的 open issues")
    targets_parser.add_argument("--issues", required=True)
    targets_parser.add_argument("--title", required=True)
    targets_parser.set_defaults(handler=_targets)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
