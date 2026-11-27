"""Rejudge the frozen after candidates with the original LiveCodeBench container."""
import argparse
import json
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from replay import ROOT, load_datasets, sha

REV = "28fef95ea8c9f7a547c8329f2cd3d32b92c1fa24"
IMAGE = "pi-lcb-submission:py312"


def run(args):
    repo = args.lcb.resolve()
    rev = subprocess.check_output(["git","-c",f"safe.directory={repo.as_posix()}","-C",str(repo),
                                  "rev-parse","HEAD"],text=True).strip()
    if rev != REV:
        raise RuntimeError("LiveCodeBench revision differs from the historic experiment")
    image = subprocess.check_output(["docker","image","inspect","--format","{{.Id}}",IMAGE],text=True).strip()
    registry = json.loads((ROOT / "evidence/registry.json").read_bytes())
    private = load_datasets(args.dataset,registry)
    report = dict(engine=IMAGE,image_id=image,livecodebench_commit=rev,
                  time=datetime.now(timezone.utc).isoformat(),rows=[])
    for row in registry:
        if not row["frozen"]:
            continue
        task = row["id"]
        code = ROOT / "after" / (task + ".py")
        cases = [(s["input"],s["expected"]) for s in row["samples"]]
        cases.extend((s["input"],s["output"]) for s in private[task])
        name = "week4-judge-" + uuid.uuid4().hex[:12]
        with tempfile.TemporaryDirectory() as directory:
            trial = Path(directory)
            shutil.copyfile(code,trial / "candidate.py")
            sample = {"input_output":json.dumps({"inputs":[i for i,o in cases],"outputs":[o for i,o in cases],"fn_name":None})}
            (trial / "sample.json").write_text(json.dumps(sample),encoding="utf8")
            cmd = ["docker","run","--rm","--name",name,"--network","none","--memory","2g","--cpus","2",
                   "--pids-limit","256","--mount",f"type=bind,source={repo},target=/lcb,readonly",
                   "--mount",f"type=bind,source={trial},target=/trial",
                   "--mount",f"type=bind,source={ROOT / 'judge.py'},target=/app/verify.py,readonly",
                   IMAGE,"python","/app/verify.py"]
            try:
                subprocess.run(cmd,check=True,timeout=240)
            except subprocess.TimeoutExpired:
                subprocess.run(["docker","rm","-f",name],capture_output=True)
                result = dict(error="container_timeout_240s")
            else:
                result = json.loads((trial / "judge-result.json").read_bytes())
            record = {key:result[key] for key in ("passed","total","results","reward","error","judge_platform","judge_python") if key in result}
            record.update(id=task,after_sha256=sha(code.read_bytes()),dataset_sha256=row["data_sha256"],
                          groups_available=len(cases),error_code=(result.get("metadata") or {}).get("error_code"))
            report["rows"].append(record)
        temp = args.output.with_suffix(".tmp")
        temp.write_text(json.dumps(report,indent=2),encoding="utf8")
        temp.replace(args.output)
        print(task,record.get("reward"),record.get("passed"),record.get("total"),flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lcb",type=Path,required=True)
    p.add_argument("--dataset",action="append",type=Path,required=True)
    p.add_argument("--output",type=Path,default=ROOT / "evidence/official-after.json")
    run(p.parse_args())
