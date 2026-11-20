"""Run the offline ReasoningBank pilot on the official held-out split."""

import argparse
import json
import os
import subprocess
import sys
import uuid
from collections import Counter
from pathlib import Path

from reasoning_bank import (
    MemoryIndex,
    digest,
    extraction_prompt,
    inject,
    parse_cards,
    read_json,
    training_evidence,
    validate_bank,
    write_json,
)

ROOT = Path(__file__).resolve().parent
QUOTAS = {"easy": 1, "medium": 1, "hard": 1}
ARMS = ("vanilla", "reasoningbank")
SHARDS = ["test.jsonl", *(f"test{i}.jsonl" for i in range(2, 7))]
METHOD = "Offline ReasoningBank adaptation (judge labels, sparse TF-IDF cosine, top-1)"


def split_data():
    split = read_json(ROOT / "data/paper-split.json")
    if set(split["train"]) & set(split["test"]):
        raise ValueError("Train/test split overlaps")
    return split


def freeze(path, value):
    if path.exists():
        if read_json(path) != value:
            raise ValueError(
                f"Configuration changed; use a new run directory: {path.name}"
            )
        return
    write_json(path, value)


def select(job):
    import requests

    path = job / "selected-test-tasks.json"
    if path.exists() and (job / "selection.json").exists():
        _, selection = read_selection(job)
        print(json.dumps(selection, indent=2))
        return
    source = read_json(ROOT / "sources.json")
    test = set(split_data()["test"])
    revision = source["dataset_revision"]
    rows, seen, counts = [], set(), Counter()
    for shard in SHARDS:
        url = (
            "https://huggingface.co/datasets/livecodebench/code_generation_lite/"
            f"resolve/{revision}/{shard}"
        )
        with requests.get(url, stream=True, timeout=(20, 90)) as response:
            response.raise_for_status()
            for line in response.iter_lines(chunk_size=65536):
                if not line:
                    continue
                row = json.loads(line)
                task, level = row["question_id"], row["difficulty"]
                if (
                    task in test
                    and task not in seen
                    and counts[level] < QUOTAS.get(level, 0)
                ):
                    rows.append(row)
                    seen.add(task)
                    counts[level] += 1
                if counts == QUOTAS:
                    break
        if counts == QUOTAS:
            break
    if counts != QUOTAS:
        raise ValueError(f"Could not fill the fixed difficulty quotas: {dict(counts)}")
    write_json(path, rows)
    selection = {
        "revision": revision,
        "policy": "First official test ID of each difficulty, in release shard and row order",
        "quotas": QUOTAS,
        "tasks": [
            {"id": r["question_id"], "difficulty": r["difficulty"]} for r in rows
        ],
        "data_sha256": digest(path.read_bytes()),
    }
    freeze(job / "selection.json", selection)
    print(json.dumps(selection, indent=2))


def read_selection(job):
    path = job / "selected-test-tasks.json"
    selection = read_json(job / "selection.json")
    raw = path.read_bytes()
    if digest(raw) != selection["data_sha256"]:
        raise ValueError("Test selection hash mismatch")
    if selection["revision"] != read_json(ROOT / "sources.json")["dataset_revision"]:
        raise ValueError("Unexpected dataset revision")
    rows = json.loads(raw)
    tasks = [{"id": r["question_id"], "difficulty": r["difficulty"]} for r in rows]
    ids = {r["id"] for r in tasks}
    if (
        len(ids) != len(rows)
        or ids - set(split_data()["test"])
        or Counter(r["difficulty"] for r in tasks) != QUOTAS
        or tasks != selection["tasks"]
    ):
        raise ValueError("Selection is outside the official test split or pilot quotas")
    return rows, selection


def configure(job, command, lcb_repo, tools=None):
    import yaml
    from run_experiment import load_config

    job.mkdir(parents=True, exist_ok=True)
    domain_file = job / "domain.yaml"
    domain_file.write_text(
        yaml.safe_dump(
            {
                "lcb_repo": str(lcb_repo),
                "split_file": str(ROOT / "data/paper-split.json"),
                "release_version": "release_v6",
                "agent_timeout": 600,
                "test_timeout": 6,
            }
        ),
        encoding="utf-8",
    )
    config_file = job / "config.yaml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "agent": {"name": "pi", "command": command, "tools": tools},
                "agent_configs": {"pi": str(ROOT / "agent/pi.yaml.example")},
                "domain": {"name": "code_implementation", "config": str(domain_file)},
                "job_dir": str(job),
                "trials": 1,
                "parallel": 1,
                "max_retries": 0,
            }
        ),
        encoding="utf-8",
    )
    load_config(str(config_file))


def call_distiller(agent, prompt, directory, label):
    session = f"{label}-{uuid.uuid4().hex[:8]}"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        result = agent.call_agent(prompt, session, timeout=240)
        if result.get("completion_status") != "completed":
            error = (result.get("stderr") or result.get("error") or "").lower()
            reason = (
                "provider credentials missing"
                if "no api key" in error
                else result["completion_status"]
            )
            raise RuntimeError(
                f"Pi {label} failed ({reason}). Check the local Pi provider configuration."
            )
        usage = agent.collect_session(session, directory)
        return result["response"], usage, result.get("elapsed_sec")
    finally:
        agent.teardown_mcp()


def distill(job, args):
    if args.train_results is None:
        raise ValueError(
            "distill requires --train-results with scored training trajectories"
        )
    records = training_evidence(args.train_results, split_data())
    # Bound prompt size without using the held-out tasks or their results.
    if len(records) > 20:
        raise ValueError("This pilot accepts up to 20 training trajectories per bank")
    prompt = extraction_prompt(records)
    provenance = [
        {k: r[k] for k in ("task", "outcome", "result_sha256", "session_sha256")}
        for r in records
    ]
    plan = {
        "method": METHOD,
        "extractor": "Pi 1.5.0 / thingo/qwen3.5-plus",
        "prompt_sha256": digest(prompt.encode()),
        "training": provenance,
    }
    freeze(job / "distillation-plan.json", plan)
    if args.review_only:
        preview = job / "distillation-prompt.txt"
        preview.write_bytes(prompt.encode("utf-8"))
        print(f"Prepared {len(records)} training excerpts for local review: {preview}")
        return

    from run_experiment import get_agent

    bank_path = job / "bank.json"
    if bank_path.exists():
        bank = read_json(bank_path)
        if bank["plan"] != plan:
            raise ValueError("Existing bank was created from different training input")
        validate_bank(bank["cards"], {r["task"] for r in records})
        print(f"Frozen bank: {len(bank['cards'])} memories")
        return
    configure(job / "distillation", args.pi_command, args.lcb_repo, tools=[])
    response, usage, elapsed = call_distiller(
        get_agent("pi"), prompt, job / "distillation", "distillation"
    )
    cards = parse_cards(response, {r["task"] for r in records})
    freeze(
        bank_path,
        {"plan": plan, "cards": cards, "usage": usage, "agent_seconds": elapsed},
    )
    print(
        f"Frozen bank: {len(cards)} memories, {len(records)} scored training trajectories"
    )


def evaluate(job, args):
    from run_experiment import (
        ENVIRONMENT_NOTE,
        RecordedDomain,
        get_agent,
        livecode,
        make_judge,
        run_all,
    )

    rows, selection = read_selection(job)
    bank_path = job / "bank.json"
    bank_raw = bank_path.read_bytes()
    bank = json.loads(bank_raw)
    allowed = {row["task"] for row in bank["plan"]["training"]}
    if not allowed or allowed - set(split_data()["train"]):
        raise ValueError("Bank provenance is outside the official train split")
    cards = validate_bank(bank["cards"], allowed)
    index = MemoryIndex(cards)
    matches = {r["question_id"]: index.retrieve(r["question_content"]) for r in rows}
    judge = args.lcb_repo.resolve()
    commit = subprocess.check_output(
        ["git", "-C", str(judge), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != read_json(ROOT / "sources.json")["livecodebench_commit"]:
        raise ValueError("Use the LiveCodeBench checkout pinned in sources.json")
    freeze(
        job / "evaluation-plan.json",
        {
            "method": METHOD,
            "selection": selection,
            "bank_sha256": digest(bank_raw),
            "model": "thingo/qwen3.5-plus",
            "pi_expected": "1.5.0",
            "judge_revision": commit,
            "harness_note_sha256": digest(ENVIRONMENT_NOTE.encode()),
            "experiment_code_sha256": digest(
                Path(__file__).read_bytes() + (ROOT / "reasoning_bank.py").read_bytes()
            ),
            "arms": list(ARMS),
            "trials_per_arm": 1,
            "parallel": 1,
            "agent_timeout_sec": 600,
            "judge_test_timeout_sec": 6,
            "retries": 0,
            "retrieval": {
                task: [{"index": i, "score": round(score, 6)} for i, score, _ in items]
                for task, items in matches.items()
            },
        },
    )
    configure(job, args.pi_command, judge)
    sys.path.insert(0, str(judge))
    from lcb_runner.benchmarks.code_generation import CodeGenerationProblem

    class PilotDomain(RecordedDomain):
        environment_note = ENVIRONMENT_NOTE

        def __init__(self, arm):
            super().__init__()
            self.arm = arm

        def build_prompt(self, task, env_info):
            prompt = super().build_prompt(task, env_info)
            return (
                inject(prompt, matches[task["name"]])
                if self.arm == "reasoningbank"
                else prompt
            )

    options = argparse.Namespace(
        split="test",
        task=None,
        trials=1,
        parallel=1,
        live=False,
        max_retries=0,
        parallel_trials=False,
        submit_interval=0,
        disk_budget=None,
    )
    for arm in ARMS:
        arm_dir = job / arm
        arm_dir.mkdir(exist_ok=True)
        domain = PilotDomain(arm)
        domain._problems = {
            row["question_id"]: CodeGenerationProblem(**row) for row in rows
        }
        tasks = domain.load_tasks(options)
        if {t["name"] for t in tasks} != set(matches):
            raise ValueError("Domain adapter dropped a frozen test problem")
        livecode._verify_code = make_judge(judge, arm_dir)
        run_all(tasks, domain, get_agent("pi"), arm_dir, options)
    report(job)


def trial_summary(path):
    if not path.is_file():
        return None
    result = read_json(path)
    agent = result.get("agent_result") or {}
    verifier = result.get("verifier_result") or {}
    usage = result.get("token_usage") or {}
    status = agent.get("completion_status")
    if result.get("exception_info") or status not in {"completed", "timeout"}:
        outcome = "infrastructure_error"
    elif status == "timeout":
        outcome = "agent_timeout"
    elif verifier.get("error"):
        outcome = "infrastructure_error"
    elif verifier.get("reward") == 1:
        outcome = "passed"
    else:
        outcome = "failed"
    return {
        "outcome": outcome,
        "test_groups_passed": verifier.get("passed"),
        "test_groups_total": verifier.get("total"),
        "tokens": usage.get("total"),
        "agent_seconds": agent.get("elapsed_sec"),
        "tool_calls": usage.get("tool_call_count"),
        "tool_errors": usage.get("tool_error_count"),
        "result_sha256": digest(path.read_bytes()),
    }


def report(job):
    _, selection = read_selection(job)
    plan_path = job / "evaluation-plan.json"
    plan = read_json(plan_path) if plan_path.exists() else None
    pairs = []
    for item in selection["tasks"]:
        task = item["id"]
        pairs.append(
            {
                **item,
                "retrieved": plan["retrieval"][task] if plan else None,
                **{
                    arm: trial_summary(job / arm / f"{task}__trial_1/result.json")
                    for arm in ARMS
                },
            }
        )
    totals = {}
    for arm in ARMS:
        trials = [pair[arm] for pair in pairs if pair[arm] is not None]
        counts = Counter(trial["outcome"] for trial in trials)
        totals[arm] = {
            "recorded": len(trials),
            "passed": counts["passed"],
            "outcomes": dict(counts),
        }
        for field in ("tokens", "agent_seconds", "tool_calls", "tool_errors"):
            values = [trial[field] for trial in trials]
            totals[arm][field] = (
                round(sum(values), 3) if values and None not in values else None
            )
    complete = all(
        totals[arm]["recorded"] == len(pairs)
        and "infrastructure_error" not in totals[arm]["outcomes"]
        for arm in ARMS
    )
    summary = {
        "method": METHOD,
        "planned_pairs": len(pairs),
        "complete": complete,
        "transfer_gain_percentage_points": round(
            100
            * (totals["reasoningbank"]["passed"] - totals["vanilla"]["passed"])
            / len(pairs),
            2,
        )
        if complete
        else None,
        "arms": totals,
        "pairs": pairs,
    }
    write_json(job / "comparison.json", summary)
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("select", "distill", "evaluate", "report"))
    parser.add_argument(
        "--run-dir", type=Path, default=ROOT / "runs/reasoningbank-pilot"
    )
    parser.add_argument("--train-results", type=Path)
    parser.add_argument("--lcb-repo", type=Path, default=ROOT / ".deps/LiveCodeBench")
    parser.add_argument("--pi-command", default="pi")
    parser.add_argument(
        "--review-only",
        action="store_true",
        help="Freeze and write the exact training prompt locally without calling Pi",
    )
    args = parser.parse_args()
    if args.review_only and args.stage != "distill":
        parser.error("--review-only applies only to distill")
    if (
        args.stage == "evaluate" or args.stage == "distill" and not args.review_only
    ) and os.name != "nt":
        parser.error("The recorded Pi harness uses Windows and a Linux Docker judge")
    job = args.run_dir.resolve()
    if args.stage == "distill":
        distill(job, args)
    elif args.stage == "evaluate":
        evaluate(job, args)
    elif args.stage == "select":
        select(job)
    else:
        report(job)


if __name__ == "__main__":
    main()
