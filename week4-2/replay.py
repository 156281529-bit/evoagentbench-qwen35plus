"""Replay the fixed candidates. Default uses only public data from the repository."""
import argparse
import base64
import hashlib
import io
import json
import pickle
import platform
import subprocess
import sys
import time
import zlib
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOL = {"abc319_c": ("1e-8", False), "abc324_f": ("1e-9", True),
       "abc327_e": ("1e-6", True), "abc350_e": ("1e-6", True)}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class DataOnly(pickle.Unpickler):
    def find_class(self, module, name):
        raise ValueError("The dataset payload must be plain JSON text")


def load_datasets(files, registry):
    datasets = {}
    for path in files:
        raw = path.read_bytes()
        fingerprint = sha(raw)
        selected = {r["id"] for r in registry if r["data_sha256"] == fingerprint and r["frozen"]}
        if not selected:
            raise ValueError("Input file does not match any frozen dataset hash")
        for row in json.loads(raw):
            task = row["question_id"]
            if task in selected:
                packed = row["private_test_cases"]
                try:
                    private = json.loads(packed)
                except json.JSONDecodeError:
                    data = zlib.decompress(base64.b64decode(packed))
                    private = json.loads(DataOnly(io.BytesIO(data)).load())
                datasets[task] = private
    if files and set(datasets) != {r["id"] for r in registry if r["frozen"]}:
        raise ValueError("Provide the three frozen dataset files")
    return datasets


def compare(task, output, expected):
    lines = [l.strip() for l in output.strip().split("\n")]
    refs = [l.strip() for l in expected.strip().split("\n")]
    exact = len(lines) == len(refs)
    try:
        exact = exact and all(x == y or list(map(Decimal,x.split())) == list(map(Decimal,y.split()))
                              for x,y in zip(lines,refs))
    except InvalidOperation:
        exact = False
    if task not in TOL:
        return exact, exact
    try:
        value, ref = Decimal(output.strip()), Decimal(expected.strip())
        tolerance, relative = TOL[task]
        ok = abs(value - ref) <= Decimal(tolerance) * (max(1,abs(ref)) if relative else 1)
    except InvalidOperation:
        ok = False
    return exact, ok


def trial(task, path, case, public):
    inp = case["input"]
    expected = case.get("expected", case.get("output"))
    t = time.monotonic()
    try:
        run = subprocess.run([sys.executable, "-I", str(path)], input=inp.encode(),
                             capture_output=True, timeout=6)
        output = run.stdout.decode().strip()
        exact, statement = compare(task, output, expected) if run.returncode == 0 else (False,False)
        status = "ok" if run.returncode == 0 else "runtime_error"
    except subprocess.TimeoutExpired:
        output, exact, statement, status = "", False, False, "timeout"
    item = dict(input_sha256=sha(inp.encode()), seconds=round(time.monotonic()-t,3),
                execution=status, exact=exact, statement=statement)
    if public:
        item.update(input=inp, expected=expected, output=output)
    return item


def replay(args):
    registry = json.loads((ROOT / "evidence/registry.json").read_bytes())
    hidden = load_datasets(args.dataset, registry)
    extra = json.loads((ROOT / "evidence/probes.json").read_bytes())
    report = dict(mode="local_process_full" if hidden else "local_process_public",
                  python=platform.python_version(), platform=platform.system(),
                  time=datetime.now(timezone.utc).isoformat(), rows=[])
    for r in registry:
        task = r["id"]
        if not r["frozen"]:
            continue
        for side in args.side:
            path = ROOT / side / (task + ".py")
            row = dict(id=task, side=side, sha256=sha(path.read_bytes()))
            if side == "before" and row["sha256"] != r["before_sha256"]:
                raise ValueError("Baseline source changed")
            row["public"] = [trial(task,path,c,True) for c in r["samples"]]
            row["probes"] = [trial(task,path,c,True) for c in extra.get(task,[])]
            if hidden:
                row["private"] = [trial(task,path,c,False) for c in hidden[task]]
            report["rows"].append(row)
            print(task,side,[(k,sum(c["exact"] for c in row[k]),len(row[k]))
                             for k in ("public","private","probes") if k in row],flush=True)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            temp = args.output.with_suffix(".tmp")
            temp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
            temp.replace(args.output)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, action="append",default=[])
    parser.add_argument("--side",choices=["before","after"],action="append")
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    args.side = args.side or ["before","after"]
    replay(args)
