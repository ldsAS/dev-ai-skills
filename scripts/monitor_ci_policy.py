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

# check_updates.py 中「只屬於異動通知」的 H2 區段。同一輪同時有異動與失敗時，
# 完整報告已送進該 run 專屬的異動 issue；失敗 issue 只需失敗資訊，否則同一份
# 報告每天寄兩次（2026-10-14 起 #31 的留言幾乎都是異動 issue 的複本）。
# 採 denylist 而非 allowlist：未知標題一律保留，寧可重複，也不能漏掉失敗原因。
# tests/test_monitor_ci_policy.py 會確認這些標題仍逐字存在於 check_updates.py。
UPDATE_ONLY_HEADINGS = (
    "## 🚨 偵測到 AI 工具路徑異動",
    "## 📒 受影響的帳本主張",
    "## 🆕 帳本中查無對應主張的新路徑",
    "## ⬆️ 版本跳動（機制可能重構）",
)


for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")


def analyze_report(report_text, exit_code=0):
    """Return workflow decisions derived from report signals and exit status."""
    # Only LF/CRLF-delimited, unindented protocol lines are authoritative.
    lines = {line.removesuffix("\r") for line in report_text.split("\n")}
    updates = UPDATE_SIGNAL in lines
    failure = FAILURE_SIGNAL in lines or exit_code != 0
    baseline = BASELINE_SIGNAL in lines
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


def failure_report(report_text, run_id):
    """Return the report for the failure issue, without update-only sections.

    A section runs from its H2 heading to the next H2, ``<details>`` block,
    signal line or ``---`` footer.  When nothing is removed the report is
    returned unchanged, so a failure-only run keeps its exact wording.
    """
    if not run_id.isdigit():
        raise ValueError("run id must be digits")
    stops = ("## ", "<details>", "[SIGNAL: ", "---")
    kept, removed, skipping = [], False, False
    for line in report_text.split("\n"):
        bare = line.removesuffix("\r")
        if skipping and bare.startswith(stops):
            skipping = False
        if bare in UPDATE_ONLY_HEADINGS:
            if not removed:
                kept.append(
                    "> ℹ️ 本次另偵測到路徑或版本異動，完整內容已送至"
                    f"「🚨 偵測到 AI 工具路徑與機制異動 · run {run_id}」issue；"
                    "此處只保留檢查失敗的資訊。")
                kept.append("")
            removed = skipping = True
            continue
        if not skipping:
            kept.append(line)
    return "\n".join(kept) if removed else report_text


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


def is_dry_run(event_name, dry_run_input):
    """Only schedules and an explicit manual false may write remotely."""
    return not (
        event_name == "schedule"
        or (event_name == "workflow_dispatch" and dry_run_input == "false")
    )


def _mode(args):
    value = _github_bool(is_dry_run(args.event, args.dry_run_input))
    with open(args.github_output, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"dry_run={value}\n")
    print(f"dry_run={value}")
    return 0


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


def _failure_report(args):
    report_text = Path(args.report).read_text(encoding="utf-8")
    sys.stdout.write(failure_report(report_text, args.run_id))
    return 0


def _targets(args):
    issues = json.loads(Path(args.issues).read_text(encoding="utf-8"))
    for number in recovery_targets(issues, args.title):
        print(number)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    mode_parser = subparsers.add_parser("mode", help="決定 dry-run；未知或缺少輸入時禁止寫入")
    mode_parser.add_argument("--event", required=True)
    mode_parser.add_argument("--dry-run-input", default="")
    mode_parser.add_argument("--github-output", required=True)
    mode_parser.set_defaults(handler=_mode)

    analyze_parser = subparsers.add_parser("analyze", help="解析報告與 exit code")
    analyze_parser.add_argument("--report", required=True)
    analyze_parser.add_argument("--exit-code", type=int, default=0)
    analyze_parser.add_argument("--github-output")
    analyze_parser.set_defaults(handler=_analyze)

    failure_parser = subparsers.add_parser("failure-report", help="產生失敗 issue 用的報告（移除異動專屬區段）")
    failure_parser.add_argument("--report", required=True)
    failure_parser.add_argument("--run-id", required=True)
    failure_parser.set_defaults(handler=_failure_report)

    targets_parser = subparsers.add_parser("targets", help="列出完全同標題的 open issues")
    targets_parser.add_argument("--issues", required=True)
    targets_parser.add_argument("--title", required=True)
    targets_parser.set_defaults(handler=_targets)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
