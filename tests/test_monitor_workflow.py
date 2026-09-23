"""Evaluate the real workflow guards offline; never invoke gh, git or the network."""

import ast
import importlib.util
import itertools
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("policy", ROOT / "scripts/monitor_ci_policy.py")
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)
WORKFLOW = yaml.load(
    (ROOT / ".github/workflows/check-updates.yml").read_text(encoding="utf-8"),
    Loader=yaml.BaseLoader,
)
STEPS = {step["name"]: step for step in WORKFLOW["jobs"]["check-and-notify"]["steps"]}


def allows(step_name, values):
    """Small fail-closed evaluator for the boolean grammar used by these guards.

    This tests the checked-in expressions, not a copy of the production policy.
    A new expression syntax must first be supported explicitly by this harness.
    """
    expression = STEPS[step_name]["if"].replace("always()", "True")
    expression = re.sub(r"steps\.[a-z_]+\.(?:outputs\.[a-z_]+|outcome)",
                        lambda match: repr(values.get(match[0], "")), expression)
    expression = expression.replace("&&", " and ").replace("||", " or ")
    tree = ast.parse(expression.strip(), mode="eval")
    allowed = (ast.Expression, ast.BoolOp, ast.Compare, ast.Constant,
               ast.And, ast.Or, ast.Eq, ast.NotEq)
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise AssertionError(f"Unsupported workflow expression: {expression}")
    return eval(compile(tree, "<workflow guard>", "eval"), {"__builtins__": {}})


class MonitorWorkflowTests(unittest.TestCase):
    WRITE_STEPS = ("Notify via GitHub Issues", "Close recovered failure Issues", "Commit baseline update")

    def test_dispatch_defaults_to_dry_run(self):
        field = WORKFLOW["on"]["workflow_dispatch"]["inputs"]["dry_run"]
        self.assertEqual("boolean", field["type"])
        self.assertEqual("true", field["default"])
        self.assertEqual("true", field["required"])

    def test_mode_cli_only_explicit_live_or_schedule_can_write(self):
        for event, value in itertools.product(
            ("schedule", "workflow_dispatch", "pull_request", ""),
            ("true", "false", "", "False", "unexpected"),
        ):
            with self.subTest(event=event, value=value), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "outputs"
                with redirect_stdout(StringIO()):
                    POLICY.main(["mode", "--event", event, "--dry-run-input", value,
                                 "--github-output", str(output)])
                expected = "false" if event == "schedule" or (
                    event == "workflow_dispatch" and value == "false") else "true"
                self.assertEqual(f"dry_run={expected}\n", output.read_text(encoding="utf-8"))

    def test_all_three_write_steps_skip_dry_run_and_unknown_mode(self):
        for mode, updates, failure, baseline, outcome in itertools.product(
            ("true", "", "unexpected"), ("true", "false"), ("true", "false"),
            ("true", "false"), ("success", "failure", "skipped"),
        ):
            values = {"steps.mode.outputs.dry_run": mode, "steps.check.outcome": outcome,
                      "steps.check.outputs.updates": updates, "steps.check.outputs.failure": failure,
                      "steps.check.outputs.baseline": baseline}
            for name in self.WRITE_STEPS + ("Summarize report with Copilot", "Prepend summary to report"):
                with self.subTest(step=name, values=values):
                    self.assertFalse(allows(name, values))

    def test_live_mode_keeps_original_write_decisions(self):
        for updates, failure, baseline, outcome in itertools.product(
            ("true", "false"), ("true", "false"), ("true", "false"),
            ("success", "failure", "skipped"),
        ):
            values = {"steps.mode.outputs.dry_run": "false", "steps.check.outcome": outcome,
                      "steps.check.outputs.updates": updates, "steps.check.outputs.failure": failure,
                      "steps.check.outputs.baseline": baseline}
            good = outcome == "success"
            expected = (good and "true" in (updates, failure), good and failure == "false",
                        good and baseline == "true")
            for name, decision in zip(self.WRITE_STEPS, expected):
                with self.subTest(step=name, values=values):
                    self.assertEqual(decision, allows(name, values))

    def test_dry_run_retains_report_and_failure_status(self):
        for failure in (False, True):
            report = POLICY.FAILURE_SIGNAL if failure else "no changes"
            decision = POLICY.analyze_report(report)
            values = {"steps.mode.outputs.dry_run": "true", "steps.check.outcome": "success",
                      "steps.check.outputs.should_fail": str(decision["should_fail"]).lower()}
            self.assertTrue(allows("Save report in job summary", values))
            self.assertEqual(failure, allows("Fail workflow when checks failed", values))

    def test_mode_output_is_wired_to_checker(self):
        self.assertEqual("mode", STEPS["Resolve run mode"]["id"])
        self.assertIn("monitor_ci_policy.py mode", STEPS["Resolve run mode"]["run"])
        step = STEPS["Run check script"]
        self.assertEqual("${{ steps.mode.outputs.dry_run }}", step["env"]["DRY_RUN"])
        self.assertIn('if [ "$DRY_RUN" != \'false\' ]; then', step["run"])
        self.assertIn("args+=(--dry-run)", step["run"])
        self.assertIn('check_updates.py "${args[@]}"', step["run"])

    def test_actual_check_shell_preserves_baseline_in_dry_run_and_reports_errors(self):
        bash = shutil.which("bash")
        git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        if os.name == "nt" and git_bash.exists():
            bash = str(git_bash)
        if not bash:
            self.skipTest("Bash required to execute the workflow shell; CI runs on Ubuntu")
        # Execute the checked-in shell verbatim except for selecting this Python.
        # Only the network checker is replaced; report parsing uses the real policy.
        shell = STEPS["Run check script"]["run"].replace(
            "python scripts/", shlex.quote(Path(sys.executable).as_posix()) + " scripts/")
        for mode, failure in itertools.product(("true", "false", "", "unexpected"), (False, True)):
            with self.subTest(mode=mode, failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "scripts").mkdir()
                shutil.copyfile(ROOT / "scripts/monitor_ci_policy.py", root / "scripts/monitor_ci_policy.py")
                (root / "scripts/check_updates.py").write_text(
                    'import json, os, sys\nfrom pathlib import Path\n'
                    'Path("args.json").write_text(json.dumps(sys.argv[1:]))\n'
                    'if "--dry-run" not in sys.argv: Path("baseline").write_text("changed")\n'
                    'print("[SIGNAL: UPDATE_DETECTED]\\n[SIGNAL: BASELINE_CHANGED]")\n'
                    'sys.exit(3 if os.environ["FIXTURE_FAILURE"] == "true" else 0)\n',
                    encoding="utf-8", newline="\n")
                (root / "baseline").write_text("original", encoding="utf-8")
                env = dict(os.environ, DRY_RUN=mode, FIXTURE_FAILURE=str(failure).lower(),
                           GITHUB_OUTPUT=(root / "outputs").as_posix())
                result = subprocess.run([bash, "-e", "-o", "pipefail", "-c", shell],
                                        cwd=root, env=env, capture_output=True,
                                        encoding="utf-8", errors="replace")
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual([] if mode == "false" else ["--dry-run"],
                                 json.loads((root / "args.json").read_text(encoding="utf-8")))
                self.assertEqual("changed" if mode == "false" else "original",
                                 (root / "baseline").read_text(encoding="utf-8"))
                outputs = dict(line.split("=", 1) for line in
                               (root / "outputs").read_text(encoding="utf-8").splitlines())
                self.assertEqual(str(failure).lower(), outputs["should_fail"])
                self.assertIn("[SIGNAL: UPDATE_DETECTED]", (root / "report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
