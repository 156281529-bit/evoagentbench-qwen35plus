"""Use the original RSI-Flow Spring REST entry point for the graph's match step."""
import json
from urllib.request import Request, urlopen

FLOW = "@week4.evoagentbench/FAILURE_DIAGNOSIS"
NODES = ["WEEK4_DIAGNOSE", "WEEK4_ROUTE"]


def registration(endpoint):
    with urlopen(endpoint + "/week4/registration", timeout=8) as response:
        state = json.load(response)
    if state.get("flow") != FLOW or not all(state.get(k) is True for k in ["assembled", *NODES]):
        raise ValueError("Native flow or annotated nodes are missing")
    return state


def dispatch(endpoint, task, public, probes):
    observations = {"task":task, "public":public, "probes":probes}
    payload = {"flowId":FLOW,"params":{"observations":json.dumps(observations,ensure_ascii=False)}}
    request = Request(endpoint + "/api/engine/flow",json.dumps(payload).encode(),
                      {"Content-Type":"application/json; charset=utf-8"})
    with urlopen(request,timeout=10) as response:
        envelope = json.load(response)
    if envelope.get("result") is not True or envelope.get("status") != 200:
        raise ValueError("Native flow rejected the input")
    receipt = json.loads(envelope["data"]["value"]["result"])
    if (receipt.get("task") != task or receipt.get("flow") != FLOW or receipt.get("nodes") != NODES
            or receipt.get("outcome") not in ("eligible","handoff") or not receipt.get("invocation")):
        raise ValueError("Invalid native dispatch receipt")
    return receipt
