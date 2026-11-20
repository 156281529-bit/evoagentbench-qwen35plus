import json

import pytest

from reasoning_bank import (
    MemoryIndex,
    inject,
    parse_cards,
    training_evidence,
    write_json,
)
from run_reasoning_bank import ARMS, report


def test_distillation_rejects_held_out_trajectories(tmp_path):
    write_json(tmp_path / "attempt" / "result.json", {"task_name": "held-out"})
    with pytest.raises(ValueError, match="outside the train split"):
        training_evidence(tmp_path, {"train": ["training"], "test": ["held-out"]})


def test_only_ranked_training_card_is_injected():
    memory = [
        {
            "title": "Binary search",
            "description": "Find a monotonic feasibility boundary",
            "content": "Check whether the predicate stays true after the boundary.",
            "source_tasks": ["training-1"],
        },
        {
            "title": "Stack reduction",
            "description": "Remove adjacent matching symbols",
            "content": "Pop pairs and recheck after each deletion.",
            "source_tasks": ["training-2"],
        },
    ]
    with pytest.raises(ValueError, match="available train tasks"):
        parse_cards(json.dumps(memory), {"training-1"})
    index = MemoryIndex(parse_cards(json.dumps(memory), {"training-1", "training-2"}))
    text = inject("Solve the task.", index.retrieve("Find a monotonic boundary"))
    assert "Binary search" in text
    assert "Stack reduction" not in text and "training-1" not in text
    assert (
        inject("Solve the task.", index.retrieve("geometry polygon"))
        == "Solve the task."
    )


def test_report_needs_two_valid_trials_per_pair(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "run_reasoning_bank.read_selection",
        lambda _: ([], {"tasks": [{"id": "held-out", "difficulty": "hard"}]}),
    )
    paths = [tmp_path / arm / "held-out__trial_1" / "result.json" for arm in ARMS]
    write_json(paths[0], {"agent_result": {"completion_status": "error"}})
    write_json(
        paths[1],
        {
            "agent_result": {"completion_status": "completed"},
            "verifier_result": {"reward": 1},
        },
    )
    report(tmp_path)
    incomplete = json.loads((tmp_path / "comparison.json").read_text())
    assert incomplete["transfer_gain_percentage_points"] is None
    write_json(
        paths[0],
        {
            "agent_result": {"completion_status": "completed"},
            "verifier_result": {"reward": 0},
        },
    )
    report(tmp_path)
    complete = json.loads((tmp_path / "comparison.json").read_text())
    assert complete["transfer_gain_percentage_points"] == 100
