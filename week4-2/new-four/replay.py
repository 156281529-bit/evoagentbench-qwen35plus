"""Replay the four published code pairs on their recorded public observations."""
import json
import subprocess
import sys
from pathlib import Path

from audit import audit

ROOT = Path(__file__).resolve().parent
CALL = """
import json,runpy,sys,typing
source,method=sys.argv[1:]
namespace=runpy.run_path(source,init_globals=vars(typing).copy())
args=[json.loads(line) for line in sys.stdin.read().splitlines()]
print(json.dumps(getattr(namespace['Solution'](),method)(*args)))
"""


def replay():
    audit()
    rows = json.loads((ROOT.parent / "four-new-repairs.json").read_bytes())["records"]
    results = []
    methods = {"3638": "makeStringGood"}
    for row in rows:
        task = row["receipt"]["id"]
        cases = row["route"]["public"] + row["route"]["probes"]
        summary = {"id": task, "public_cases": len(cases)}
        for side in ("before", "after"):
            source = ROOT / side / (task + ".py")
            command = [sys.executable, "-I", str(source)]
            if task in methods:
                command = [sys.executable, "-I", "-c", CALL, str(source), methods[task]]
            outputs = []
            for case in cases:
                result = subprocess.run(command, input=case["input"], text=True,
                                        capture_output=True, timeout=6, check=True)
                actual = result.stdout.strip()
                outputs.append(actual)
                if side == "after":
                    assert actual == case["expected"].strip(), (task, actual, case["expected"])
                else:
                    assert actual == case["output"].replace("\r\n", "\n").strip(), (task, "Baseline output changed")
            summary[side + "_outputs"] = outputs
        results.append(summary)
    print(json.dumps({"status": "passed", "rows": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    replay()
