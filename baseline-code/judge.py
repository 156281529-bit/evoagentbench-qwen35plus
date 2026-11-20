"""Execute the installed, unmodified LiveCodeBench judge under Linux."""

import json
import platform
from pathlib import Path

from lcb_runner.evaluation.compute_code_generation_metrics import check_correctness


if __name__ == "__main__":
    trial = Path("/trial")
    sample = json.loads((trial / "sample.json").read_text())
    code = (trial / "candidate.py").read_text()
    try:
        results, metadata = check_correctness(sample, code, timeout=6, debug=False)
        results = [int(value) for value in results]
        passed = sum(value == 1 for value in results)
        report = {
            "reward": float(bool(results) and passed == len(results)),
            "passed": passed,
            "total": len(results),
            "results": results,
            "metadata": metadata,
            "judge_python": platform.python_version(),
            "judge_platform": platform.system(),
        }
    except Exception as exc:
        report = {"reward": 0.0, "error": str(exc), "passed": 0, "total": 0}
    (trial / "judge-result.json").write_text(json.dumps(report, default=str, indent=2))
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ("results", "metadata")}
        )
    )
