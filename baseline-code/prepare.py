"""Fetch fixed evaluation dependencies and the five recorded tasks."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent


def prepare_data():
    source = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    ids = set(source["task_ids"])
    url = f"https://huggingface.co/datasets/livecodebench/code_generation_lite/resolve/{source['dataset_revision']}/{source['dataset_file']}"
    rows = []
    with requests.get(url, stream=True, timeout=(20, 60)) as response:
        response.raise_for_status()
        for line in response.iter_lines(chunk_size=1024 * 1024):
            if not line:
                continue
            row = json.loads(line)
            if row["question_id"] in ids:
                rows.append(row)
                if len(rows) == len(ids):
                    break
    data = json.dumps(rows, ensure_ascii=False).encode("utf-8")
    if hashlib.sha256(data).hexdigest() != source["selection_sha256"]:
        raise RuntimeError("Downloaded task data does not match the recorded selection")
    target = ROOT / "data/selected-tasks.json"
    target.write_bytes(data)
    print(f"DATA READY: {len(rows)} tasks; SHA256 verified")


def prepare_judge():
    source = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    target = ROOT / ".deps/LiveCodeBench"
    if not target.exists():
        target.parent.mkdir(exist_ok=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                "https://github.com/LiveCodeBench/LiveCodeBench.git",
                str(target),
            ],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(target),
                "fetch",
                "--depth",
                "1",
                "origin",
                source["livecodebench_commit"],
            ],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(target),
                "checkout",
                "--detach",
                source["livecodebench_commit"],
            ],
            check=True,
        )
    commit = subprocess.check_output(
        ["git", "-C", str(target), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != source["livecodebench_commit"]:
        raise RuntimeError(
            "Existing judge checkout differs; use a fresh .deps directory"
        )
    subprocess.run(
        ["docker", "build", "-t", "pi-lcb-submission:py312", str(ROOT)], check=True
    )
    print("JUDGE READY: pinned LiveCodeBench source + Python 3.12 Docker image")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-only", action="store_true")
    parser.add_argument("--judge-only", action="store_true")
    args = parser.parse_args()
    if not args.judge_only:
        prepare_data()
    if not args.data_only:
        prepare_judge()
