"""Execute the existing graph. Only reviewed, frozen local solutions are eligible."""
import argparse
import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from replay import ROOT, load_datasets, sha, trial
from native_client import dispatch, registration


def read(name):
    return json.loads((ROOT / name).read_bytes())


GRAPH = read("platform/workflow.json")
NEXT = {(e["from"],e["outcome"]): e["to"] for e in GRAPH["edges"]}
REGISTRY = [r for r in read("evidence/registry.json") if r["frozen"]]
PROBES = read("evidence/probes.json")
RECIPES = read("recipes.json")


def run_case(r, private, formal, locks, native_engine=None):
    task = r["id"]
    left = ROOT / "before" / (task + ".py")
    right = ROOT / "after" / (task + ".py")
    cases = r["samples"] + PROBES.get(task,[])
    before_hash, after_hash = sha(left.read_bytes()), sha(right.read_bytes())
    evidence = {"id":task, "trace":[], "recipe":None, "attempts":0,"handoffs":0,
                "before_sha256":before_hash,"after_sha256":after_hash}
    node = GRAPH["entry"]
    for _ in GRAPH["nodes"]:
        if node == "baseline":
            if before_hash != r["before_sha256"]:
                raise ValueError("baseline digest differs")
            evidence["before"] = {"passed":r["groups_passed"],"reached":r["groups_reached"],
                                  "result_sha256":r["result_sha256"]}
            outcome = "failed"
        elif node == "public":
            observations = [trial(task,left,c,True) for c in cases]
            evidence["public_before"] = observations
            outcome = "observed"
        elif node == "match":
            if native_engine:
                count = len(r["samples"])
                result = dispatch(native_engine, task, observations[:count], observations[count:])
                evidence["native"] = result
                witnessed = result["outcome"] == "eligible"
            else:
                witnessed = any(not c["exact"] and c["execution"] == "ok" for c in observations)
            eligible = witnessed and task in RECIPES and locks.get(task) == after_hash
            if eligible:
                evidence["recipe"] = RECIPES[task]["id"]
            outcome = "eligible" if eligible else "handoff"
        elif node == "repair":
            evidence["attempts"] += 1
            outcome = "revised"
        elif node == "verify":
            checks = [trial(task,right,c,True) for c in cases]
            evidence["public_after"] = checks
            public_ok = all(c["exact"] and c["execution"] == "ok" for c in checks)
            if private and public_ok:
                hidden = [trial(task,right,c,False) for c in private[task]]
                evidence["private_local"] = {"tested":len(hidden),"passed":sum(c["exact"] for c in hidden),
                    "statement":sum(c["statement"] for c in hidden)}
            receipt = formal.get(task, {})
            formal_ok = (receipt.get("after_sha256") == after_hash and
                         receipt.get("dataset_sha256") == r["data_sha256"])
            if formal_ok:
                evidence["fixed_after"] = receipt
            passed = public_ok and formal_ok and receipt.get("reward") == 1
            outcome = "passed" if passed else "failed"
            if not passed:
                evidence["reason"] = ("public_regression" if not public_ok else
                    "fixed_judge_failure" if formal_ok else "awaiting_linux_judge")
        elif node == "human":
            evidence["handoffs"] += 1
            outcome = "recorded"
        elif node == "record":
            evidence["trace"].append([node,"saved"])
            return evidence
        evidence["trace"].append([node,outcome])
        node = NEXT[(node,outcome)]
    raise ValueError("graph did not terminate")


def serve(args):
    private = load_datasets(args.dataset,REGISTRY)
    locks = {r["id"]:r["sha256"] for r in read("evidence/local-full.json")["rows"] if r["side"]=="after"}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def send(self, code, data):
            body = json.dumps(data,ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/workflow":
                self.send(200,dict(definition=GRAPH,cases=[r["id"] for r in REGISTRY]))
            elif self.path == "/latest" and args.output.is_file():
                self.send(200,json.loads(args.output.read_bytes()))
            else:
                self.send(404,{})

        def do_POST(self):
            if self.path != "/run":
                return self.send(404,{})
            if not lock.acquire(blocking=False):
                return self.send(409,{"error":"已有批次正在运行"})
            try:
                length = int(self.headers.get("Content-Length","0"))
                if not 0 < length < 16384:
                    return self.send(400,{"error":"请求长度无效"})
                req = json.loads(self.rfile.read(length))
                edges = {(e["from"],e["outcome"],e["to"]) for e in req["edges"]}
                required = {(a,b,c) for (a,b),c in NEXT.items()}
                if req["workflow"] != GRAPH["id"] or edges != required or len(req["edges"]) != len(edges):
                    return self.send(400,{"error":"画布与已确认的流程定义不一致"})
                receipt = ROOT / "evidence/official-after.json"
                formal = {r["id"]:r for r in json.loads(receipt.read_bytes())["rows"]} if receipt.is_file() else {}
                state = registration(args.native_engine) if args.native_engine else None
                rows = [run_case(r,private,formal,locks,args.native_engine) for r in REGISTRY]
                report = dict(workflow=GRAPH["id"], time=datetime.now(timezone.utc).isoformat(),
                    graph_sha256=sha((ROOT/"platform/workflow.json").read_bytes()), rows=rows)
                if state:
                    report["native_registration"] = state
                temp = args.output.with_suffix(".tmp")
                temp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
                temp.replace(args.output)
                self.send(200,report)
            except OSError as err:
                self.send(503,{"error":str(err)})
            except (ValueError,KeyError,TypeError) as err:
                self.send(400,{"error":str(err)})
            finally:
                lock.release()

    ThreadingHTTPServer(("127.0.0.1",args.port),Handler).serve_forever()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port",type=int,default=39913)
    p.add_argument("--native-engine", help="URL of the RSI-Flow Spring service")
    p.add_argument("--dataset",type=Path,action="append",default=[])
    p.add_argument("--output",type=Path,default=ROOT / "evidence/platform-batch.json")
    serve(p.parse_args())
