"""Reproduce the recorded v1/v2 five-task Windows-host baseline."""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "framework/src"))
from config import get_agent, load_config  # noqa: E402
from domains.code_implementation import livecode  # noqa: E402
from runner import run_all  # noqa: E402
from audit import audit, write_report  # noqa: E402

ENVIRONMENT_NOTE = (
    "\n\n### Execution environment (fixed harness information)\n"
    "This run uses Windows and the powershell tool. Use PowerShell 5.1-compatible syntax. "
    "Use separate statements or ';' instead of '&&'. PowerShell does not support Bash-style "
    "stdin redirection '< file' or heredocs. To feed a saved input file to Python, use "
    "Get-Content -Raw -LiteralPath 'input.txt' | python 'solution.py'. "
    "Python is available on PATH. The exec tool mentioned above refers to your available "
    "powershell tool. Keep files inside the assigned working directory and return the final "
    "Python code in the originally requested format."
)


class RecordedDomain(livecode.LiveCodeBenchAdapter):
    environment_note = ""

    def build_prompt(self, task, env_info):
        return super().build_prompt(task, env_info) + self.environment_note


def make_judge(lcb_repo, job_dir):
    def verify(problem, code, timeout=6):
        directory = job_dir / "judge-work" / uuid.uuid4().hex[:12]
        directory.mkdir(parents=True)
        (directory / "sample.json").write_text(
            json.dumps(problem.get_evaluation_sample()), encoding="utf-8"
        )
        (directory / "candidate.py").write_text(code, encoding="utf-8")
        name = "pi-lcb-" + uuid.uuid4().hex[:12]
        command = [
            "docker",
            "run",
            "--rm",
            "--name",
            name,
            "--network",
            "none",
            "--memory",
            "2g",
            "--cpus",
            "2",
            "--pids-limit",
            "256",
            "--mount",
            f"type=bind,source={lcb_repo},target=/lcb,readonly",
            "--mount",
            f"type=bind,source={directory},target=/trial",
            "--mount",
            f"type=bind,source={ROOT / 'judge.py'},target=/app/verify.py,readonly",
            "pi-lcb-submission:py312",
            "python",
            "/app/verify.py",
        ]
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8", timeout=240
            )
            if result.returncode:
                return {
                    "reward": 0,
                    "passed": 0,
                    "total": 0,
                    "error": result.stderr[-2000:],
                }
            return json.loads(
                (directory / "judge-result.json").read_text(encoding="utf-8")
            )
        except subprocess.TimeoutExpired:
            return {"reward": 0, "passed": 0, "total": 0, "error": "judge_timeout_240s"}
        finally:
            subprocess.run(
                ["docker", "rm", "-f", name], capture_output=True, timeout=15
            )

    return verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("v1", "v2"), default="v2")
    parser.add_argument("--data", type=Path, default=ROOT / "data/selected-tasks.json")
    parser.add_argument("--lcb-repo", type=Path, default=ROOT / ".deps/LiveCodeBench")
    parser.add_argument("--pi-command", default="pi")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if os.name != "nt":
        raise RuntimeError(
            "The recorded harness requires a Windows host; the judge runs in Linux Docker"
        )
    source = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    data = args.data.read_bytes()
    if hashlib.sha256(data).hexdigest() != source["selection_sha256"]:
        raise RuntimeError("Task data differs from the recorded five-task selection")
    rows = json.loads(data)
    lcb_repo = args.lcb_repo.resolve()
    sys.path.insert(0, str(lcb_repo))
    from lcb_runner.benchmarks.code_generation import CodeGenerationProblem

    job = ROOT / "runs" / args.variant
    job.mkdir(parents=True, exist_ok=True)
    domain_config = {
        "lcb_repo": str(lcb_repo),
        "split_file": str(ROOT / "data/paper-split.json"),
        "release_version": "release_v6",
        "agent_timeout": 600,
        "test_timeout": 6,
    }
    (job / "domain.yaml").write_text(yaml.safe_dump(domain_config), encoding="utf-8")
    config = {
        "agent": {"name": "pi", "command": args.pi_command},
        "agent_configs": {"pi": str(ROOT / "agent/pi.yaml.example")},
        "domain": {"name": "code_implementation", "config": str(job / "domain.yaml")},
        "job_dir": str(job),
        "trials": 1,
        "parallel": 1,
        "max_retries": 0,
    }
    (job / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    load_config(str(job / "config.yaml"))
    domain = RecordedDomain()
    domain.environment_note = ENVIRONMENT_NOTE if args.variant == "v2" else ""
    domain._problems = {
        row["question_id"]: CodeGenerationProblem(**row) for row in rows
    }
    livecode._verify_code = make_judge(lcb_repo, job)
    run_args = argparse.Namespace(
        split="train",
        task=",".join(source["task_ids"]),
        trials=1,
        parallel=1,
        live=True,
        max_retries=0,
        parallel_trials=False,
        submit_interval=0,
        disk_budget=None,
    )
    tasks = domain.load_tasks(run_args)
    if len(tasks) != 5:
        raise RuntimeError("Expected exactly five tasks from the paper train split")
    manifest = {
        "variant": args.variant,
        "model": "thingo/qwen3.5-plus",
        "pi_version_expected": "1.5.0",
        "task_ids": source["task_ids"],
        "data_sha256": source["selection_sha256"],
        "environment_note_sha256": hashlib.sha256(
            domain.environment_note.encode()
        ).hexdigest(),
        "trials": 1,
        "parallel": 1,
        "max_retries": 0,
        "timeout_sec": 600,
    }
    manifest_path = job / "manifest.json"
    if (
        manifest_path.exists()
        and json.loads(manifest_path.read_text(encoding="utf-8")) != manifest
    ):
        raise RuntimeError("Refusing to resume a run with changed configuration")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"READY: {args.variant}, 5 tasks, results={job}", flush=True)
    if args.prepare_only:
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    run_all(tasks, domain, get_agent("pi"), job, run_args)
    write_report(audit(job, args.data), job / "diagnosis")


if __name__ == "__main__":
    main()
