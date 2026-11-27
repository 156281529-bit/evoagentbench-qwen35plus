"""Run the supplementary candidate in the exact image used by the original cohort."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "week4-2"
sys.path.insert(0, str(BASE))
from replay import load_datasets, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lcb", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    task = "abc382_g"
    old_run = json.loads((BASE / "evidence/official-after.json").read_bytes())
    repo = args.lcb.resolve()
    rev = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if rev != old_run["livecodebench_commit"]:
        raise ValueError("LiveCodeBench revision differs from v2")
    image = old_run["image_id"]
    subprocess.run(["docker", "image", "inspect", image], stdout=subprocess.DEVNULL, check=True)
    registry = json.loads((BASE / "evidence/registry.json").read_bytes())
    row = next(r for r in registry if r["id"] == task)
    data = load_datasets([args.dataset], [dict(row, frozen=True)])[task]
    cases = [(r["input"], r["expected"]) for r in row["samples"]] + [(r["input"], r["output"]) for r in data]
    sample = {"inputs": [x for x, y in cases], "outputs": [y for x, y in cases], "fn_name": None}
    name = "week4-supplement-" + uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory() as folder:
        trial = Path(folder)
        code = ROOT / (task + ".py")
        shutil.copyfile(code, trial / "candidate.py")
        (trial / "sample.json").write_text(json.dumps({"input_output": json.dumps(sample)}), encoding="utf8")
        cmd = ["docker", "run", "--rm", "--name", name, "--network", "none", "--memory", "2g", "--cpus", "2",
               "--pids-limit", "256", "--mount", f"type=bind,source={repo},target=/lcb,readonly",
               "--mount", f"type=bind,source={trial},target=/trial", "--mount",
               f"type=bind,source={BASE / 'judge.py'},target=/app/verify.py,readonly",
               image, "python", "/app/verify.py"]
        try:
            subprocess.run(cmd, check=True, timeout=240)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
            raise
        result = json.loads((trial / "judge-result.json").read_bytes())
    verdict = {key: result[key] for key in ("passed", "total", "results", "reward", "judge_platform",
                                            "judge_python", "error") if key in result}
    verdict.update(task=task, after_sha256=sha(code.read_bytes()), dataset_sha256=row["data_sha256"],
                   image_id=image, livecodebench_commit=rev, available_groups=len(cases),
                   time=datetime.now(timezone.utc).isoformat())
    args.out.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf8")
    print(verdict)


if __name__ == "__main__":
    main()

