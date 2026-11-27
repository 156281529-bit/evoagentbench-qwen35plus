"""Reproduce the case search, paired routing and optional hash-locked hidden replay."""
import argparse
from bisect import bisect_right
from collections import deque
from functools import lru_cache
from itertools import product
import json
from pathlib import Path
from random import Random
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "week4-2"
sys.path.insert(0, str(BASE))
from replay import load_datasets, sha, trial
from native_client import dispatch, registration


def tile(k, x, y):
    i, j = x // k, y // k
    return i, j, (y if (i + j) % 2 == 0 else x) % k


@lru_cache(maxsize=65536)
def around(k, current):
    i, j, z = current
    horizontal = (i + j) % 2 == 0
    result = set()
    for index in range(k):
        x = i * k + (index if horizontal else z)
        y = j * k + (z if horizontal else index)
        for x1, y1 in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
            result.add(tile(k, x1, y1))
    result.discard(current)
    return result


def grid_oracle(k, sx, sy, targets):
    origin = tile(k, sx, sy)
    wanted = {tile(k, *t) for t in targets}
    known = {origin: 0}
    queue = deque([origin])
    while wanted:
        current = queue.popleft()
        wanted.discard(current)
        for neighbor in around(k, current):
            if neighbor not in known:
                known[neighbor] = known[current] + 1
                queue.append(neighbor)
    return [known[tile(k, *t)] for t in targets]


def tile_cases():
    for k in (2, 3):
        points = list(product(range(-2, 3), repeat=2))
        for sx, sy in points:
            for (x, y), expected in zip(points, grid_oracle(k, sx, sy, points)):
                yield "grid", (k, sx, sy, x, y), expected
    rng = Random(382186)
    for k in (2, 3, 4, 5, 6, 7, 9, 13):
        for sx, sy in ((0, 0), (-k, 0), (1, k-1), (-3, -2)):
            targets = sorted({(rng.randrange(-13*k, 13*k), rng.randrange(4*k, 13*k))
                              for _ in range(40)})
            for (x, y), expected in zip(targets, grid_oracle(k, sx, sy, targets)):
                yield "far", (k, sx, sy, x, y), expected
    # Translation by two whole blocks preserves tile orientation and every edge.
    for k in (2, 3, 7, 13):
        shift = ((10**16 - 100) // (2*k)) * (2*k)
        targets = list(product(range(-5, 6), repeat=2))
        for (x, y), expected in zip(targets, grid_oracle(k, 0, 0, targets)):
            yield "limits", (k, shift, -shift, shift+x, -shift+y), expected
    # Within one horizontal block, two boundary crossings connect any two rows.
    for k in (10**12, 10**16):
        rows = (0, 1, k//2, k-2, k-1)
        for a, b in product(rows, repeat=2):
            yield "limits", (k, 0, a, k-1, b), min(abs(a-b), 2)
        for a in rows:
            yield "limits", (k, -1, a, 0, a), 1


def run_numbers(path, stdin):
    process = subprocess.run([sys.executable, "-I", str(path)], input=stdin, text=True,
                             capture_output=True, timeout=10, check=True)
    return list(map(int, process.stdout.split()))


@lru_cache(None)
def forest(size):
    if size == 0:
        return [()]
    return [(tree,) + tail for first in range(1, size + 1)
            for tree in trees(first) for tail in forest(size - first)]


@lru_cache(None)
def trees(size):
    return [(len(children),) + tuple(v for child in children for v in child)
            for children in forest(size - 1)]


def sequence_cases():
    for n in range(1, 6):
        valid = sorted(trees(n))
        if n <= 3:
            candidates = product(range(n), repeat=n)
        else:
            candidates = {v[:-1] + (last,) for v in valid for last in (0, 1, n-1)}
        for seq in sorted(candidates):
            yield seq, bisect_right(valid, seq)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path)
    p.add_argument("--endpoint")
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    task = "abc382_g"
    baseline = BASE / "before" / (task + ".py")
    repaired = ROOT / (task + ".py")
    entries = json.loads((BASE / "evidence/registry.json").read_bytes())
    entry = next(r for r in entries if r["id"] == task)
    assert sha(baseline.read_bytes()) == entry["before_sha256"]
    report = {"candidates": {}, "suites": {}, "counterexamples": {}}
    cases = list(tile_cases())
    stdin = str(len(cases)) + "\n" + "".join(" ".join(map(str, case)) + "\n" for _, case, _ in cases)
    old = run_numbers(baseline, stdin)
    new = run_numbers(repaired, stdin)
    assert len(old) == len(new) == len(cases)
    for name in ("grid", "far", "limits"):
        rows = [(c, e, a, b) for (suite, c, e), a, b in zip(cases, old, new) if suite == name]
        report["suites"][name] = counts(rows)
        misses = sorted((r for r in rows if r[1] != r[2]),
                        key=lambda r: (sum(abs(x) for x in r[0][1:]), r[0]))
        report["counterexamples"][name] = misses[:4]
    seq_paths = [BASE / s / "arc186_d.py" for s in ("before", "after")]
    seq_rows = []
    for seq, expected in sequence_cases():
        data = str(len(seq)) + "\n" + " ".join(map(str, seq)) + "\n"
        a, b = (run_numbers(path, data) for path in seq_paths)
        assert len(a) == len(b) == 1
        seq_rows.append((seq, expected, a[0], b[0]))
    report["suites"]["polish"] = counts(seq_rows)
    report["counterexamples"]["polish"] = [r for r in seq_rows if r[1] != r[2]][:4]
    report["candidate_hashes"] = {str(p.relative_to(ROOT.parent)).replace("\\", "/"): sha(p.read_bytes())
                                  for p in [baseline, repaired, *seq_paths]}
    if args.dataset:
        private = load_datasets([args.dataset], [dict(entry, frozen=True)])[task]
        report["dataset_sha256"] = entry["data_sha256"]
    for name, path in (("before", baseline), ("after", repaired)):
        row = {"public": [trial(task, path, c, True) for c in entry["samples"]]}
        if args.dataset:
            row["private"] = [trial(task, path, c, False) for c in private]
        report["candidates"][name] = row
    if args.endpoint:
        report["native"] = {"registration": registration(args.endpoint), "pairs": {}}
        for name, suite, path in [(task, "grid", baseline), ("arc186_d", "polish", seq_paths[0])]:
            row = next(r for r in entries if r["id"] == name)
            public = [trial(name, path, c, True) for c in row["samples"]]
            first, expected, _, _ = report["counterexamples"][suite][0]
            size = 1 if name == task else len(first)
            counterexample = {"input": str(size) + "\n" + " ".join(map(str, first)) + "\n",
                              "expected": str(expected)}
            obs = trial(name, path, counterexample, True)
            passing = {"input": "1\n2 0 0 0 0\n" if name == task else "1\n0\n",
                       "expected": "0" if name == task else "1"}
            control = trial(name, path, passing, True)
            assert all(r["exact"] for r in public) and control["exact"] and not obs["exact"]
            report["native"]["pairs"][name] = {
                "public": public, "passing_probe": control, "failing_probe": obs,
                "public_only": dispatch(args.endpoint, name, public, []),
                "plus_passing": dispatch(args.endpoint, name, public, [control]),
                "plus_failing": dispatch(args.endpoint, name, public, [obs])}
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(report["suites"]))
    for name, row in report["candidates"].items():
        print(name, {k: [sum(v["exact"] for v in rows), len(rows)] for k, rows in row.items()})


def counts(rows):
    return {"total": len(rows), "before_pass": sum(e == a for _, e, a, b in rows),
            "after_pass": sum(e == b for _, e, a, b in rows)}


if __name__ == "__main__":
    main()

