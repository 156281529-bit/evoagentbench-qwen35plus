"""Validate the four new code pairs against the published receipts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IDS = {"3638", "arc195_d", "abc400_g", "abc374_d"}


def audit():
    rows = json.loads((ROOT.parent / "four-new-repairs.json").read_bytes())["records"]
    assert {row["receipt"]["id"] for row in rows} == IDS
    for row in rows:
        receipt = row["receipt"]
        task = receipt["id"]
        assert receipt == json.loads((ROOT / "repairs" / (task + ".json")).read_bytes())
        assert row["route"] == json.loads((ROOT / "routes" / (task + ".json")).read_bytes())
        for side in ("before", "after"):
            code = (ROOT / side / (task + ".py")).read_bytes()
            assert hashlib.sha256(code).hexdigest() == receipt[side + "_sha256"]
            assert code.decode("utf8").replace("\r\n", "\n") == row[side]
        assert receipt["before"]["reward"] == 0
        assert receipt["after"]["reward"] == 1
        assert receipt["after"]["results"] == [1] * receipt["available"]
        assert receipt["after"]["judge_platform"] == "Linux"
        assert receipt["invocation"] == row["route"]["route"]["invocation"]
        assert row["route"]["route"]["outcome"] == "eligible"
    return sorted(IDS)


if __name__ == "__main__":
    print("Four new repairs verified:", ", ".join(audit()))
