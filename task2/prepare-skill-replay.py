"""Derive an offline RSI-Flow replay fixture from an existing completed pilot."""

import argparse
import json
import sys
from pathlib import Path

BASELINE = Path(__file__).resolve().parents[1] / "baseline-code"
sys.path.insert(0, str(BASELINE))

from reasoning_bank import FIELDS, HEADER, MemoryIndex, digest, inject, read_json, validate_bank, write_json
from run_reasoning_bank import read_selection, split_data


def prompt_from(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        message = json.loads(line).get("message") or {}
        if message.get("role") == "user":
            parts = [part["text"] for part in message["content"] if part["type"] == "text"]
            return "\n".join(parts).replace("\r\n", "\n")
    raise ValueError(f"No user message in {path}")


def make_fixture(run, output, workflow_only=False, completed_pairs_only=False):
    rows, selection = read_selection(run)
    bank_path = run / "bank.json"
    bank = read_json(bank_path)
    bank_sha = digest(bank_path.read_bytes())
    train_ids = {entry["task"] for entry in bank["plan"]["training"]}
    if not train_ids or not train_ids <= set(split_data()["train"]):
        raise ValueError("The frozen bank contains a non-training source")
    cards = validate_bank(bank["cards"], train_ids)
    index = MemoryIndex(cards)
    if workflow_only:
        tasks = workflow_cases(rows, index)
    else:
        tasks = scored_cases(run, rows, selection, bank_sha, index, completed_pairs_only)
    write_json(output, {
        "mode": "offline_workflow_verification" if workflow_only else "offline_replay",
        "bankSha256": bank_sha,
        "header": HEADER,
        "cards": [
            {**{key: card[key] for key in FIELDS}, "vector": vector}
            for card, vector in zip(cards, index.vectors)
        ],
        "tasks": tasks,
    })
    print(f"Local replay fixture: {len(tasks)} tasks, {len(cards)} memory items.")


def workflow_cases(rows, index):
    from run_experiment import ENVIRONMENT_NOTE, RecordedDomain

    adapter = RecordedDomain()
    adapter.environment_note = ENVIRONMENT_NOTE
    tasks = []
    for row in rows:
        question = row["question_content"]
        prompt = adapter.build_prompt(row, {})
        matches = index.retrieve(question)
        memory_id, score = matches[0][:2] if matches else (-1, 0.0)
        tasks.append({
            "id": row["question_id"],
            "vector": index.vector(index.tokens(question)),
            "basePrompt": prompt,
            "expectedMemoryIndex": memory_id,
            "expectedScore": score,
            "expectedPromptSha256": digest(inject(prompt, matches).encode("utf-8")),
        })
    return tasks


def scored_cases(run, rows, selection, bank_sha, index, completed_pairs_only=False):
    plan = read_json(run / "evaluation-plan.json")
    comp = read_json(run / "comparison.json")
    if selection != plan["selection"] or bank_sha != plan["bank_sha256"]:
        raise ValueError("Expected a matching frozen bank and selection")
    if not comp["complete"] and not completed_pairs_only:
        raise ValueError("Expected a completed evaluation with a matching frozen bank and selection")
    paired = {pair["id"]: pair for pair in comp["pairs"]}
    tasks = []
    for row in rows:
        task = row["question_id"]
        if completed_pairs_only and any(
            (paired[task][arm] or {}).get("outcome") not in {"passed", "failed"}
            for arm in ("vanilla", "reasoningbank")
        ):
            continue
        matches = plan["retrieval"][task]
        match = matches[0] if matches else {"index": -1, "score": 0.0}
        folder = f"{task}__trial_1"
        paths = {arm: run / arm / folder for arm in ("vanilla", "reasoningbank")}
        scores = {}
        for arm, path in paths.items():
            raw = (path / "result.json").read_bytes()
            result = json.loads(raw)
            if result["task_name"] != task or digest(raw) != paired[task][arm]["result_sha256"]:
                raise ValueError(f"The archived result differs from the recorded trial: {arm}/{task}")
            scores[arm] = int(result["verifier_result"]["reward"])
        vanilla = prompt_from(paths["vanilla"] / "session.jsonl")
        evolved = prompt_from(paths["reasoningbank"] / "session.jsonl")
        tasks.append({
            "id": task,
            "vector": index.vector(index.tokens(row["question_content"])),
            "basePrompt": vanilla,
            "expectedMemoryIndex": match["index"],
            "expectedScore": match["score"],
            "expectedPromptSha256": digest(evolved.encode("utf-8")),
            "archivedVanillaReward": scores["vanilla"],
            "archivedReasoningBankReward": scores["reasoningbank"],
        })
    if not tasks:
        raise ValueError("No held-out task has two recorded verdicts for replay")
    return tasks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=BASELINE / "runs/reasoningbank-pilot")
    parser.add_argument("--output", type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--workflow-only", action="store_true",
        help="Verify retrieval and prompt construction without archived judge scores",
    )
    group.add_argument(
        "--completed-pairs-only", action="store_true",
        help="Replay only prompts from completed pairs with two judge verdicts",
    )
    options = parser.parse_args()
    make_fixture(options.run_dir, options.output, options.workflow_only, options.completed_pairs_only)
