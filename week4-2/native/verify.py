"""Check native receipts against the frozen public diagnoses, plus one held-out invocation."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnose import diagnose
from native_client import FLOW, NODES, dispatch, registration


def read(name):
    return json.loads((ROOT / "evidence" / name).read_bytes())


def verify(endpoint):
    batch = read("native-batch.json")
    frozen = {row["id"]:row for row in read("public-pairs.json")["rows"] if row["side"] == "before"}
    formal = {row["id"]:row for row in read("official-after.json")["rows"]}
    reserve = read("transfer.json")["reserve"]
    invocations = set()
    assert batch["native_registration"]["assembled"] and batch["native_registration"]["flow"] == FLOW
    assert set(frozen) == {r["id"] for r in batch["rows"]} and len(batch["rows"]) == 10
    for row in batch["rows"]:
        task = row["id"]
        receipt = row["native"]
        old = frozen[task]
        assert receipt["flow"] == FLOW and receipt["task"] == task and receipt["nodes"] == NODES
        assert receipt["tag"] == diagnose(old["public"],old["probes"])
        assert receipt["outcome"] == "eligible" and ["match","eligible"] in row["trace"]
        assert row["fixed_after"] == formal[task]
        invocations.add(receipt["invocation"])
    assert len(invocations) == 10
    if endpoint:
        state = registration(endpoint)
        result = dispatch(endpoint,reserve["id"],reserve["public"],[])
        holdout = {"registration":state,"input":{"task":reserve["id"],"public":reserve["public"],"probes":[]},
                   "response":result}
    else:
        holdout = read("native-holdout.json")
        result = holdout["response"]
    assert result["task"] == reserve["id"] and result["nodes"] == NODES and result["flow"] == FLOW
    assert result["tag"] == reserve["diagnosis"] and result["outcome"] == "handoff"
    assert result["invocation"] not in invocations
    if endpoint:
        (ROOT / "evidence/native-holdout.json").write_text(json.dumps(holdout,ensure_ascii=False,indent=2)+"\n",
                                                           encoding="utf8")
    print("Ten distinct native invocations match the frozen diagnoses; the reserve case routes to human review.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--engine",help="Optional live local RSI-Flow URL for the holdout request")
    verify(p.parse_args().engine)
