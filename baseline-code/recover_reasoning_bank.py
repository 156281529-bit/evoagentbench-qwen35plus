"""Run one supplemental ReasoningBank attempt for an unjudged held-out case."""

import argparse
import json
import msvcrt
import shutil
import subprocess
import sys
from pathlib import Path

from reasoning_bank import MemoryIndex, digest, inject, read_json, validate_bank, write_json
from run_reasoning_bank import ROOT, configure, read_selection, split_data, trial_summary

ANSWER_ONLY = (
    "\n\nReturn a complete, runnable Python program in one fenced python code block. "
    "Give the program directly, without a prose explanation. /no_think"
)
FINALIZE = (
    "Finish the solution now. Use the original question and retrieved experience above. "
    "Return the complete runnable Python program in one fenced python code block, without "
    "any prose explanation. /no_think"
)


def first_prompt(session):
    for line in session.read_text(encoding="utf-8").splitlines():
        message = json.loads(line).get("message") or {}
        if message.get("role") == "user":
            return "\n".join(
                item["text"] for item in message["content"] if item["type"] == "text"
            ).replace("\r\n", "\n")
    raise ValueError("The original session does not contain its input prompt")


def prepare(run, task_id, judge):
    from run_experiment import ENVIRONMENT_NOTE, RecordedDomain

    rows, selection = read_selection(run)
    plan = read_json(run / "evaluation-plan.json")
    comparison = read_json(run / "comparison.json")
    planned_ids = [item["id"] for item in selection["tasks"]]
    if (
        [pair["id"] for pair in comparison["pairs"]] != planned_ids
        or comparison["planned_pairs"] != len(planned_ids)
        or any(
            pair[arm]["outcome"] not in {"passed", "failed"}
            for pair in comparison["pairs"]
            for arm in ("vanilla", "reasoningbank")
            if (pair["id"], arm) != (task_id, "reasoningbank")
        )
    ):
        raise ValueError("The original comparison has additional missing or invalid verdicts")
    pair = next(row for row in comparison["pairs"] if row["id"] == task_id)
    arm = pair["reasoningbank"]
    initial_dir = run / "reasoningbank" / f"{task_id}__trial_1"
    initial_raw = (initial_dir / "result.json").read_bytes()
    initial = json.loads(initial_raw)
    if (
        pair["vanilla"]["outcome"] not in {"passed", "failed"}
        or arm["outcome"] != "infrastructure_error"
        or digest(initial_raw) != arm["result_sha256"]
        or initial.get("last_stop_reason") != "length"
        or (initial.get("verifier_result") or {}).get("judge_platform")
    ):
        raise ValueError("Expected the original output-limit attempt with no judge verdict")

    bank_bytes = (run / "bank.json").read_bytes()
    bank = json.loads(bank_bytes)
    training_ids = {entry["task"] for entry in bank["plan"]["training"]}
    if not training_ids or training_ids - set(split_data()["train"]):
        raise ValueError("Unexpected sources for the frozen memory bank")
    judge_revision = subprocess.check_output(
        ["git", "-C", str(judge), "rev-parse", "HEAD"], text=True
    ).strip()
    source_hash = digest(
        (ROOT / "run_reasoning_bank.py").read_bytes()
        + (ROOT / "reasoning_bank.py").read_bytes()
    )
    if (
        plan["selection"] != selection
        or plan["bank_sha256"] != digest(bank_bytes)
        or plan["harness_note_sha256"] != digest(ENVIRONMENT_NOTE.encode())
        or plan["experiment_code_sha256"] != source_hash
        or plan["judge_revision"] != judge_revision
        or plan["model"] != "thingo/qwen3.5-plus"
        or plan["pi_expected"] != "1.5.0"
        or plan["agent_timeout_sec"] != 600
        or plan["judge_test_timeout_sec"] != 6
    ):
        raise ValueError("The supplement must use the original frozen evaluator and settings")

    row = next(row for row in rows if row["question_id"] == task_id)
    index = MemoryIndex(validate_bank(bank["cards"], training_ids))
    memories = index.retrieve(row["question_content"])
    retrieval = [{"index": i, "score": round(score, 6)} for i, score, _ in memories]
    if retrieval != plan["retrieval"][task_id]:
        raise ValueError("The retrieved memory differs from the original attempt")

    class RecoveryDomain(RecordedDomain):
        environment_note = ENVIRONMENT_NOTE
        answer_instruction = ""

        def build_prompt(self, task, env_info):
            if self.answer_instruction == FINALIZE:
                return FINALIZE
            return inject(super().build_prompt(task, env_info), memories) + self.answer_instruction

    domain = RecoveryDomain()
    prompt = domain.build_prompt(row, {})
    if prompt != first_prompt(initial_dir / "session.jsonl"):
        raise ValueError("The supplemental prompt differs from the original attempt")
    return domain, row, plan, comparison, digest(prompt.encode())


def recover(args):
    from run_experiment import get_agent, livecode, make_judge
    from config import get_config
    from runner import run_task_trials

    domain, row, plan, comparison, prompt_hash = prepare(
        args.original, args.task, args.lcb_repo
    )
    variant = "same_configuration"
    continuation_hash = None
    if args.continue_from:
        domain.answer_instruction = FINALIZE
        variant = "resume_after_output_limit"
        continuation_hash = digest(args.continue_from.read_bytes())
        if first_prompt(args.continue_from) != first_prompt(
            args.original / "reasoningbank" / f"{args.task}__trial_1" / "session.jsonl"
        ):
            raise ValueError("Continuation must use the same question and retrieved memory")
    elif args.finish_answer or args.compatible_answer:
        domain.answer_instruction = ANSWER_ONLY
        variant = "answer_only_thinking_off" if args.finish_answer else "answer_only_no_tools"
    if domain.answer_instruction:
        prompt_hash = digest(domain.build_prompt(row, {}).encode())
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "run.lock").open("a+b") as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        configure(
            args.output, args.pi_command, args.lcb_repo,
            tools=[] if args.compatible_answer or args.continue_from else None,
        )
        sys.path.insert(0, str(args.lcb_repo))
        from lcb_runner.benchmarks.code_generation import CodeGenerationProblem

        domain._problems = {args.task: CodeGenerationProblem(**row)}
        (task,) = domain.load_tasks(argparse.Namespace(split="test", task=args.task))
        livecode._verify_code = make_judge(args.lcb_repo, args.output)
        result = args.output / f"{args.task}__trial_1" / "result.json"
        if result.is_file():
            print(f"Reading saved supplemental attempt for {args.task}.", flush=True)
        else:
            print(f"Running {args.task} with ReasoningBank. Waiting for model and judge.", flush=True)
        agent = get_agent("pi")
        try:
            if args.finish_answer:
                get_config()["agent"]["reasoningEffort"] = "off"
                agent._ensure_temp_config()
                model_file = Path(agent._temp_workspace) / "agent" / "models.json"
                models = read_json(model_file)
                provider = models["providers"]["thingo"]
                model = next(item for item in provider["models"] if item["id"] == "qwen3.5-plus")
                model["reasoning"] = True
                model.setdefault("compat", {})["thinkingFormat"] = "qwen"
                write_json(model_file, models)
            if args.continue_from:
                call = agent.call_agent

                def continue_agent(prompt, session_id, timeout=600, cwd=None):
                    shutil.copyfile(args.continue_from, agent._session_file(session_id))
                    return call(prompt, session_id, timeout=timeout, cwd=cwd)

                agent.call_agent = continue_agent
            run_task_trials(task, domain, agent, args.output, trials=1, max_retries=0)
        finally:
            agent.teardown_mcp()

        trial = trial_summary(result)
        recorded = read_json(result)
        verifier = recorded.get("verifier_result") or {}
        judged = (
            trial["outcome"] in {"passed", "failed"}
            and verifier.get("judge_platform") == "Linux"
            and verifier.get("total", 0) > 0
        )
        if judged:
            checks = verifier["results"]
            passed = sum(check == 1 for check in checks)
            if (
                len(checks) != verifier["total"]
                or passed != verifier["passed"]
                or float(passed == len(checks)) != verifier["reward"]
            ):
                raise ValueError("The supplement's judge verdict is internally inconsistent")
        total = comparison["planned_pairs"]
        vanilla = comparison["arms"]["vanilla"]["passed"]
        reasoning = comparison["arms"]["reasoningbank"]["passed"]
        if judged:
            reasoning += int(trial["outcome"] == "passed")
        summary = {
            "task": args.task,
            "arm": "reasoningbank",
            "model": plan["model"],
            "variant": variant,
            "continued_session_sha256": continuation_hash,
            "judge_revision": plan["judge_revision"],
            "prompt_sha256": prompt_hash,
            "original_comparison_sha256": digest((args.original / "comparison.json").read_bytes()),
            "supplemental_attempt": trial,
            "model_stop_reason": recorded.get("last_stop_reason"),
            "judge_executed": judged,
            "post_recovery_comparison": {
                "tasks": total,
                "vanilla_passed": vanilla,
                "reasoningbank_passed": reasoning,
                "complete": judged,
                "gain_percentage_points": round(100 * (reasoning - vanilla) / total, 2)
                if judged else None,
                "includes_supplemental_attempt": True,
            },
        }
        write_json(args.output / "recovery-summary.json", summary)
        print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lcb-repo", type=Path, required=True)
    parser.add_argument("--task", default="abc327_e")
    parser.add_argument("--pi-command", default="pi.cmd")
    parser.add_argument("--check", action="store_true")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--finish-answer", action="store_true")
    modes.add_argument("--compatible-answer", action="store_true")
    modes.add_argument("--continue-from", type=Path)
    args = parser.parse_args()
    args.original, args.output, args.lcb_repo = (
        path.resolve() for path in (args.original, args.output, args.lcb_repo)
    )
    if args.output == args.original or args.original in args.output.parents:
        parser.error("Use a separate output directory for the supplemental attempt")
    if args.check:
        *_, prompt_hash = prepare(args.original, args.task, args.lcb_repo)
        print(f"Original configuration and prompt verified: {prompt_hash}")
    else:
        recover(args)


if __name__ == "__main__":
    main()
