"""Recreate three byte-identical cohort files from the published release JSONL shards."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def restore(shards, output):
    cohorts = json.loads((HERE / "evidence/cohorts.json").read_bytes())
    wanted = {task for cohort in cohorts for task in cohort["ids"]}
    rows = {}
    for file in shards:
        with file.open("rb") as stream:
            for line in stream:
                if line.strip():
                    row = json.loads(line)
                    task = row["question_id"]
                    if task in wanted and task not in rows:
                        rows[task] = row
    missing = wanted - rows.keys()
    if missing:
        raise ValueError("Missing tasks: " + ", ".join(sorted(missing)))
    output.mkdir(parents=True,exist_ok=True)
    for cohort in cohorts:
        data = [rows[task] for task in cohort["ids"]]
        text = json.dumps(data,ensure_ascii=False,indent=2) + "\n"
        for ending in ("\r\n","\n"):
            raw = text.replace("\n",ending).encode()
            if hashlib.sha256(raw).hexdigest() == cohort["sha256"]:
                (output / cohort["name"]).write_bytes(raw)
                break
        else:
            raise ValueError("Published data differs for " + cohort["name"])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--shard",action="append",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a = p.parse_args()
    restore(a.shard,a.output)
