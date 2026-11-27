"""Classify public observations without using task identifiers or private examples."""
import json
from replay import ROOT, trial


def diagnose(samples, probes):
    failures = [r for r in samples + probes if not r["exact"]]
    if any(r["execution"] != "ok" for r in failures):
        return "execution_failure"
    if failures and all(r["statement"] for r in failures):
        return "numeric_comparator"
    if any(not r["exact"] for r in samples):
        return "public_mismatch"
    if failures:
        return "counterexample"
    return "needs_counterexample"


if __name__ == "__main__":
    registry = json.loads((ROOT / "evidence/registry.json").read_bytes())
    pairs = json.loads((ROOT / "evidence/public-pairs.json").read_bytes())["rows"]
    tags = {r["id"]:diagnose(r["public"],r["probes"]) for r in pairs if r["side"] == "before"}
    holdout = next(r for r in registry if not r["frozen"])
    baseline = ROOT / "before" / (holdout["id"] + ".py")
    samples = [trial(holdout["id"],baseline,c,True) for c in holdout["samples"]]
    result = {"frozen_cohort":tags,"reserve":{"id":holdout["id"],"public":samples,
              "diagnosis":diagnose(samples,[]),"action":"human_review_no_frozen_repair"}}
    print(json.dumps(result,ensure_ascii=False,indent=2))
