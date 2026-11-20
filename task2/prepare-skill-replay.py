"""Derive an offline RSI-Flow replay fixture from an existing completed pilot."""

import argparse
import json
import sys
from pathlib import Path

BASELINE = Path(__file__).resolve().parents[1] / "baseline-code"
sys.path.insert(0, str(BASELINE))

from reasoning_bank import FIELDS, HEADER, MemoryIndex, digest, read_json, validate_bank, write_json
from run_reasoning_bank import read_selection, split_data


def prompt_from(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        message = json.loads(line).get("message") or {}
        if message.get("role") == "user":
            parts = [part["text"] for part in message["content"] if part["type"] == "text"]
            return "\n".join(parts).replace("\r\n", "\n")
    raise ValueError(f"No user message in {path}")


def make_fixture(run, output):
    rows, selection = read_selection(run)
    plan = read_json(run / "evaluation-plan.json")
    comp = read_json(run / "comparison.json")
    bank_path = run / "bank.json"
    bank = read_json(bank_path)
    bank_sha = digest(bank_path.read_bytes())
    if selection != plan["selection"] or bank_sha != plan["bank_sha256"] or not comp["complete"]:
        raise ValueError("Expected a completed pilot with a matching frozen bank and selection")
    train_ids = {entry["task"] for entry in bank["plan"]["training"]}
    if not train_ids <= set(split_data()["train"]):
        raise ValueError("The frozen bank contains a non-training source")
    cards = validate_bank(bank["cards"], train_ids)
    index = MemoryIndex(cards)
    paired = {pair["id"]: pair for pair in comp["pairs"]}
    tasks = []
    for row in rows:
        task = row["question_id"]
        matches = plan["retrieval"][task]
        if len(matches) != 1:
            raise ValueError("This replay expects exactly one retrieved item per task")
        match = matches[0]
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
    write_json(output, {
        "bankSha256": bank_sha,
        "header": HEADER,
        "cards": [
            {**{key: card[key] for key in FIELDS}, "vector": vector}
            for card, vector in zip(cards, index.vectors)
        ],
        "tasks": tasks,
    })
    print(f"Local replay fixture: {len(tasks)} tasks, {len(cards)} memory items.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=BASELINE / "runs/reasoningbank-pilot")
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    make_fixture(options.run_dir, options.output)
