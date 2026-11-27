"""Execute the student-authored workflow on saved EvoAgentBench candidates."""

import argparse
import ast
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
from threading import Lock
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / "baseline-code"
sys.path.insert(0, str(BASELINE))
from reasoning_bank import digest, read_json, write_json
from run_experiment import make_judge


WORKFLOW = read_json(HERE / "workflow.json")
EXPERIENCE = {entry["id"]: entry for entry in read_json(HERE / "experiences.json")}
TRANSITIONS = {(edge["from"], edge["outcome"]): edge["to"] for edge in WORKFLOW["edges"]}
TOLERANCES = {
    "abc319_c": ("1e-8", False),
    "abc324_f": ("1e-9", True),
    "abc327_e": ("1e-6", True),
    "abc350_e": ("1e-6", True),
}


@dataclass(frozen=True)
class Case:
    task: str
    problem: object
    code: str
    original_result_hash: str


def result_summary(result):
    if result.get("error") or not result.get("total"):
        return {"status": "error"}
    return {"status": "pass" if result["reward"] == 1 else "fail",
            "passed": result["passed"], "groups_reached": result["total"],
            "error_code": (result.get("metadata") or {}).get("error_code")}


def public_problem(problem):
    samples = problem.public_test_cases
    return SimpleNamespace(get_evaluation_sample=lambda: {"input_output": json.dumps({
        "inputs": [sample.input for sample in samples], "outputs": [sample.output for sample in samples],
        "fn_name": problem.metadata.get("func_name"),
    })})


def tolerance_conflict(task, result):
    rule = TOLERANCES.get(task)
    metadata = result.get("metadata") or {}
    if not rule or metadata.get("error_code") != -2:
        return None
    try:
        actual = Decimal(metadata["output"].strip())
        reference = Decimal(metadata["expected"].strip())
    except (InvalidOperation, KeyError, AttributeError):
        return None
    if not (actual.is_finite() and reference.is_finite()):
        return None
    with localcontext() as context:
        context.prec = 64
        tolerance = Decimal(rule[0])
        delta = abs(actual - reference)
        bound = tolerance * max(Decimal(1), abs(reference)) if rule[1] else tolerance
        if 0 < delta <= bound:
            return {"absolute_error": str(delta), "tolerance": rule[0], "relative_allowed": rule[1]}
    return None


def debug_repair(code, public_result):
    diagnostic = public_result.get("metadata") or {}
    output, expected = diagnostic.get("output"), diagnostic.get("expected")
    if diagnostic.get("error_code") != -2 or not isinstance(output, str) or not isinstance(expected, str):
        return None
    got, wanted = output.strip().splitlines(), expected.strip().splitlines()
    if len(got) != len(wanted) + 1:
        return None
    extras = [line for i, line in enumerate(got) if line.startswith("DEBUG:") and got[:i] + got[i + 1:] == wanted]
    if len(extras) != 1:
        return None
    tree = ast.parse(code)
    lines = code.splitlines(keepends=True)
    matching = []
    for statement in ast.walk(tree):
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            continue
        call = statement.value
        if (isinstance(call.func, ast.Name) and call.func.id == "print" and not call.keywords
                and len(call.args) == 1 and isinstance(call.args[0], ast.Constant) and call.args[0].value == extras[0]
                and statement.lineno == statement.end_lineno):
            line = lines[statement.lineno - 1].strip()
            if line == ast.get_source_segment(code, statement):
                matching.append(statement)
    if len(matching) != 1:
        return None
    index = matching[0].lineno - 1
    indent = lines[index][:matching[0].col_offset]
    lines[index] = indent + "pass\n"
    revised = "".join(lines)
    compile(revised, "<candidate>", "exec")
    return revised


def execute(case, judge):
    state = {"id": case.task, "candidate_sha256": digest(case.code.encode()),
             "historic_result_sha256": case.original_result_hash, "attempts": 0, "handoffs": 0,
             "experience": None, "reason": None, "after": None, "trace": []}
    node = WORKFLOW["entry"]
    for _ in range(len(WORKFLOW["nodes"])):
        if node == "baseline":
            original = judge(case.problem, case.code)
            state["before"] = result_summary(original)
            outcome = {"pass": "passed", "fail": "failed", "error": "error"}[state["before"]["status"]]
            if outcome == "passed":
                state["after"] = state["before"]
            if outcome == "error":
                state["reason"] = "judge_infrastructure_error"
        elif node == "public":
            public = judge(public_problem(case.problem), case.code)
            state["public_before"] = result_summary(public)
            outcome = "observed"
        elif node == "match":
            conflict = tolerance_conflict(case.task, original)
            if conflict:
                state.update(experience=EXPERIENCE["numeric-comparator-conflict"]["id"],
                             reason="statement_judge_tolerance_conflict", tolerance_evidence=conflict)
                outcome = "handoff"
            else:
                revised = debug_repair(case.code, public) if state["public_before"]["status"] == "fail" else None
                if revised is None:
                    state["reason"] = "no_match_with_concrete_public_fix"
                    outcome = "handoff"
                else:
                    state["experience"] = EXPERIENCE["stdout-debug-line"]["id"]
                    outcome = "eligible"
        elif node == "repair":
            if state["attempts"] >= WORKFLOW["maxRepairs"]:
                raise RuntimeError("Repair budget exceeded")
            state["attempts"] += 1
            state["revised_sha256"] = digest(revised.encode())
            outcome = "revised"
        elif node == "verify":
            state["public_after"] = result_summary(judge(public_problem(case.problem), revised))
            if state["public_after"]["status"] == "pass":
                state["after"] = result_summary(judge(case.problem, revised))
            passed = (state["after"] or {}).get("status") == "pass"
            if not passed:
                state["reason"] = "failed_after_one_repair"
            outcome = "passed" if passed else "failed"
        elif node == "human":
            state["handoffs"] += 1
            outcome = "recorded"
        elif node == "record":
            state["trace"].append({"node": node, "outcome": "saved"})
            return state
        else:
            raise RuntimeError(f"Unknown workflow node: {node}")
        state["trace"].append({"node": node, "outcome": outcome})
        node = TRANSITIONS[(node, outcome)]
    raise RuntimeError("Workflow did not terminate")


def load_cases(roots, lcb):
    sys.path.insert(0, str(lcb))
    from lcb_runner.benchmarks.code_generation import CodeGenerationProblem

    test_split = set(read_json(BASELINE / "data/paper-split.json")["test"])
    cases = {}
    for root in roots:
        data = root / "selected-test-tasks.json"
        if not data.exists():
            data = root / "tasks.json"
        if digest(data.read_bytes()) != read_json(root / "selection.json")["data_sha256"]:
            raise ValueError("Saved dataset hash differs from its selection")
        for row in read_json(data):
            task = row["question_id"]
            if task in cases or task not in test_split:
                raise ValueError(f"Duplicate or non-test task: {task}")
            trial = root / "vanilla" / f"{task}__trial_1"
            code = trial / "verifier/solution.py"
            if code.is_file():
                cases[task] = Case(task, CodeGenerationProblem(**row), code.read_text(encoding="utf-8"),
                                   digest((trial / "result.json").read_bytes()))
    return cases


def run_cases(cases, judge):
    rows = [execute(case, judge) for case in cases]
    before_failures = sum(row["before"]["status"] == "fail" for row in rows)
    repairs = sum(row["before"]["status"] == "fail" and (row["after"] or {}).get("status") == "pass" for row in rows)
    return {"workflow": WORKFLOW["id"], "run_at": datetime.now(timezone.utc).isoformat(),
            "cases": len(rows), "before_pass": sum(x["before"]["status"] == "pass" for x in rows),
            "before_fail": before_failures, "verified_repairs": repairs,
            "repair_rate": repairs / before_failures if before_failures else None,
            "automatic_attempts": sum(row["attempts"] for row in rows),
            "human_handoffs": sum(row["handoffs"] for row in rows), "results": rows}


def serve(cases, judge, result_dir, port):
    lock = Lock()
    test_graph = {(e["from"], e["outcome"], e["to"]) for e in WORKFLOW["edges"]}

    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, value):
            payload = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path != "/workflow":
                return self.send_json(404, {"error": "Unknown endpoint"})
            self.send_json(200, {"definition": WORKFLOW, "cases": list(cases)})

        def do_POST(self):
            if self.path != "/run":
                return self.send_json(404, {"error": "Unknown endpoint"})
            if not lock.acquire(blocking=False):
                return self.send_json(409, {"error": "已有一批正在判题"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384 or self.headers.get_content_type() != "application/json":
                    raise ValueError("Invalid request")
                request = json.loads(self.rfile.read(length))
                edges = [(e["from"], e["outcome"], e["to"]) for e in request["edges"]]
                if request["workflow"] != WORKFLOW["id"] or set(edges) != test_graph or len(edges) != len(test_graph):
                    raise ValueError("Unexpected workflow topology")
                report = run_cases(cases.values(), judge)
                write_json(result_dir / "last-browser-run.json", report)
                self.send_json(200, report)
            except (ValueError, TypeError, KeyError):
                self.send_json(400, {"error": "画布结构与冻结实验结构不一致"})
            except Exception:
                self.send_json(500, {"error": "判题执行失败，请查看本机运行日志"})
                raise
            finally:
                lock.release()

    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"EvoAgentBench workflow service on 127.0.0.1:{port}, {len(cases)} candidates", flush=True)
        server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, action="append", required=True)
    parser.add_argument("--lcb", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--serve", type=int, metavar="PORT")
    args = parser.parse_args()
    lcb = args.lcb.resolve()
    revision = subprocess.check_output(["git", "-C", str(lcb), "rev-parse", "HEAD"], text=True).strip()
    if revision != read_json(BASELINE / "sources.json")["livecodebench_commit"]:
        raise ValueError("Use the pinned LiveCodeBench checkout")
    cases = load_cases(args.source_run, lcb)
    if not cases:
        raise ValueError("No saved official test candidates")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    judge = make_judge(lcb, output)
    if args.serve:
        serve(cases, judge, output, args.serve)
    else:
        write_json(output / "last-cli-run.json", run_cases(cases.values(), judge))


if __name__ == "__main__":
    main()
