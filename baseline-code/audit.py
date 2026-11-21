"""Audit completion, correctness, and recoverable tool failures separately."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_session(path):
    calls = {}
    results = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = entry.get("message", {})
        if msg.get("role") == "assistant":
            for part in msg.get("content", []):
                if part.get("type") == "toolCall":
                    calls[part.get("id")] = part
        if msg.get("role") == "toolResult":
            results.append((number, entry, msg))
    events = []
    for index, (number, entry, msg) in enumerate(results):
        if not msg.get("isError"):
            continue
        call = calls.get(msg.get("toolCallId"), {})
        command = call.get("arguments", {}).get("command", "")
        output = "\n".join(
            p.get("text", "") for p in msg.get("content", []) if p.get("type") == "text"
        )
        if "RedirectionNotSupported" in output:
            category = "powershell_input_redirection"
        elif "InvalidEndOfLine" in output and "&&" in command:
            category = "powershell_chain_operator"
        else:
            category = "other_tool_error"
        following = next(
            (
                (n, e, m)
                for n, e, m in results[index + 1 :]
                if m.get("toolName") == msg.get("toolName") and not m.get("isError")
            ),
            None,
        )
        recovery = None
        if following:
            n, e, m = following
            next_call = calls.get(m.get("toolCallId"), {})
            recovery = {
                "line": n,
                "command": next_call.get("arguments", {}).get("command"),
                "elapsed_between_events_sec": round(
                    (
                        datetime.fromisoformat(e["timestamp"])
                        - datetime.fromisoformat(entry["timestamp"])
                    ).total_seconds(),
                    2,
                ),
            }
        events.append(
            {
                "category": category,
                "session_file": str(path),
                "line": number,
                "record_id": entry.get("id"),
                "tool": msg.get("toolName"),
                "command": command,
                "output": output,
                "contains_replacement_characters": "\ufffd" in output,
                "later_successful_same_tool": recovery,
            }
        )
    return Counter(call.get("name", "unknown") for call in calls.values()), events


def audit(job_dir, dataset):
    rows = json.loads(dataset.read_text(encoding="utf-8"))
    records, all_events = [], []
    calls = Counter()
    for row in rows:
        task_id = row["question_id"]
        trial = job_dir / f"{task_id}__trial_1"
        result_path = trial / "result.json"
        record = {
            "task_id": task_id,
            "difficulty": row["difficulty"],
            "result_file": str(result_path),
            "finalized": result_path.is_file(),
        }
        if not record["finalized"]:
            record.update(
                completion_status="missing",
                passed=False,
                final_failure=None,
                pending_reason="incomplete_trial_no_result"
                if trial.is_dir()
                else "not_started",
                tool_error_count=0,
            )
            records.append(record)
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        agent, verifier = (
            result.get("agent_result", {}),
            result.get("verifier_result", {}),
        )
        status = agent.get("completion_status", "missing")
        passed = verifier.get("reward", 0) > 0 and verifier.get("total", 0) > 0
        if passed:
            failure = None
        elif result.get("exception_info"):
            failure = "runner_exception"
        elif status == "timeout":
            failure = "agent_timeout"
        elif status != "completed":
            error_text = " ".join(
                str(agent.get(key) or "") for key in ("error", "stderr", "response")
            ).lower()
            if any(
                marker in error_text
                for marker in (
                    "no api key",
                    "invalid api key",
                    "unauthorized",
                    "authentication",
                    "401",
                    "403",
                )
            ):
                failure = "provider_authentication_error"
            elif any(
                marker in error_text
                for marker in ("429", "rate limit", "too many requests")
            ):
                failure = "provider_rate_limit"
            elif any(
                marker in error_text
                for marker in (
                    "error calling llm",
                    "fetch failed",
                    "server disconnected",
                    "econnreset",
                    "502",
                    "503",
                    "504",
                )
            ):
                failure = "provider_transport_error"
            else:
                failure = "agent_error"
        elif verifier.get("error") == "no_code_extracted":
            failure = "no_code_extracted"
        elif verifier.get("error"):
            failure = "judge_or_verification_error"
        elif verifier.get("total", 0) == 0:
            failure = "empty_judge_result"
        else:
            metadata_text = str(
                verifier.get("metadata", {}).get("error_message", "")
            ).lower()
            if "time limit" in metadata_text or "timeout" in metadata_text:
                failure = "solution_time_limit"
            elif "runtime" in metadata_text:
                failure = "solution_runtime_error"
            elif "compil" in metadata_text or "syntax" in metadata_text:
                failure = "solution_compile_error"
            else:
                failure = "wrong_answer"
        session = trial / "session.jsonl"
        task_calls, events = (
            inspect_session(session) if session.is_file() else (Counter(), [])
        )
        calls.update(task_calls)
        all_events.extend({"task_id": task_id, **event} for event in events)
        record.update(
            completion_status=status,
            passed=passed,
            final_failure=failure,
            elapsed_sec=agent.get("elapsed_sec", 0),
            total_tokens=result.get("token_usage", {}).get("total", 0),
            passed_tests=verifier.get("passed", 0),
            total_tests=verifier.get("total", 0),
            tool_calls=sum(task_calls.values()),
            powershell_calls=task_calls["powershell"],
            tool_error_count=len(events),
            recovered_tool_error_count=sum(
                event["later_successful_same_tool"] is not None for event in events
            ),
            session_file=str(session),
        )
        records.append(record)
    n = len(rows)
    finalized = sum(r["finalized"] for r in records)
    completed = sum(r["completion_status"] == "completed" for r in records)
    passed = sum(r["passed"] for r in records)
    affected = sum(r["tool_error_count"] > 0 for r in records)
    categories = Counter(e["category"] for e in all_events)
    return {
        "job_dir": str(job_dir),
        "dataset_file": str(dataset),
        "difficulty_counts": dict(Counter(row["difficulty"] for row in rows)),
        "reused_trial": json.loads(
            (job_dir / "provenance.json").read_text(encoding="utf-8")
        )
        if (job_dir / "provenance.json").is_file()
        else None,
        "harness_manifest": json.loads(
            (job_dir / "harness-manifest.json").read_text(encoding="utf-8")
        )
        if (job_dir / "harness-manifest.json").is_file()
        else None,
        "planned_tasks": n,
        "finalized_tasks": finalized,
        "pending_tasks": n - finalized,
        "pending_categories": dict(
            Counter(r["pending_reason"] for r in records if not r["finalized"])
        ),
        "run_state": json.loads(
            (job_dir / "run-state.json").read_text(encoding="utf-8")
        )
        if (job_dir / "run-state.json").is_file()
        else None,
        "agent_completed_tasks": completed,
        "passed_tasks": passed,
        "agent_completion_rate": completed / n,
        "task_pass_rate": passed / n,
        "pass_rate_among_finalized": passed / finalized if finalized else None,
        "agent_completion_rate_among_finalized": completed / finalized
        if finalized
        else None,
        "final_failure_rates_among_finalized": {
            key: count / finalized
            for key, count in Counter(
                r["final_failure"] for r in records if r["final_failure"]
            ).items()
        }
        if finalized
        else {},
        "tasks_with_tool_errors": affected,
        "task_tool_error_rate": affected / n,
        "task_tool_error_rate_among_finalized": affected / finalized
        if finalized
        else None,
        "tool_calls": dict(calls),
        "all_tool_calls": sum(calls.values()),
        "tool_error_events": len(all_events),
        "tool_error_rate_per_call": len(all_events) / sum(calls.values())
        if calls
        else None,
        "powershell_error_rate_per_call": sum(
            e["tool"] == "powershell" for e in all_events
        )
        / calls["powershell"]
        if calls["powershell"]
        else None,
        "tool_error_categories": dict(categories),
        "final_failure_categories": dict(
            Counter(r["final_failure"] for r in records if r["final_failure"])
        ),
        "passed_test_groups": sum(r.get("passed_tests", 0) for r in records),
        "total_test_groups": sum(r.get("total_tests", 0) for r in records),
        "total_agent_seconds": round(sum(r.get("elapsed_sec", 0) for r in records), 1),
        "total_tokens": sum(r.get("total_tokens", 0) for r in records),
        "selection_data_sha256": sha256(dataset),
        "records": records,
        "events": all_events,
    }


def write_report(report, destination):
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "diagnosis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    n = report["planned_tasks"]
    tool_rate = report["tool_error_rate_per_call"]
    shell_rate = report["powershell_error_rate_per_call"]
    tool_rate_text = f"{tool_rate:.1%}" if tool_rate is not None else "无调用，不适用"
    shell_rate_text = (
        f"{shell_rate:.1%}" if shell_rate is not None else "无调用，不适用"
    )
    reuse = report.get("reused_trial")
    reuse_text = (
        f"复用已完成试验：{reuse.get('reused_task', reuse.get('reused_tasks', []))}；来源与SHA256见diagnosis.json。"
        if reuse
        else "本批未复用其他批次的试验。"
    )
    lines = [
        "EvoAgentBench / Pi 小批量基线诊断记录",
        "模型：thingo / qwen3.5-plus；Pi 1.5.0；每题1次；并发1；自动重试0；每题上限600秒。",
        f"计划数据：{n}道题；难度分布：{report['difficulty_counts']}。",
        f"结果目录：{report['job_dir']}",
        reuse_text,
        "",
        "一、完成、答题与工具错误分开统计",
        f"已落盘：{report['finalized_tasks']}/{n}；待运行或未落盘：{report['pending_tasks']}。待运行题不算模型失败。",
        f"Agent 正常完成：{report['agent_completed_tasks']}/{n} ({report['agent_completion_rate']:.1%})。",
        f"整题官方测试全通过：{report['passed_tasks']}/{n} ({report['task_pass_rate']:.1%})。",
        f"官方测试组：{report['passed_test_groups']}/{report['total_test_groups']}。",
        f"遇到工具错误的题目：{report['tasks_with_tool_errors']}/{n} ({report['task_tool_error_rate']:.1%})。",
        f"工具调用错误：{report['tool_error_events']}/{report['all_tool_calls']} ({tool_rate_text})。",
        f"PowerShell调用错误率：{shell_rate_text}。",
        f"最终失败分类：{report['final_failure_categories'] or '未观察到最终失败'}。",
        f"各最终失败类型占已落盘题目的比例：{report['final_failure_rates_among_finalized']}。",
        f"待运行分类：{report['pending_categories']}；执行状态：{report.get('run_state')}。",
        f"总Agent耗时：{report['total_agent_seconds']}秒；总Tokens：{report['total_tokens']}。",
        "",
        "二、逐题记录",
        "题号 | 难度 | 完成状态 | 官方测试 | 秒 | Tokens | 工具错误",
    ]
    for r in report["records"]:
        lines.append(
            f"{r['task_id']} | {r['difficulty']} | {r['completion_status']} | {r.get('passed_tests', 0)}/{r.get('total_tests', 0)} | {r.get('elapsed_sec', 0)} | {r.get('total_tokens', 0)} | {r['tool_error_count']}"
        )
    lines.extend(["", "三、错误证据与根因"])
    for e in report["events"]:
        lines.extend(
            [
                f"{e['task_id']}：{e['category']}",
                f"原命令：{e['command']}",
                f"证据：{e['session_file']} 第{e['line']}行，record_id={e['record_id']}。",
            ]
        )
        if e["later_successful_same_tool"]:
            lines.append(f"后续成功命令：{e['later_successful_same_tool']['command']}")
    lines.extend(
        [
            "",
            "初轮pilot-v1已核实：Windows PowerShell 5.1.26100.9818不支持 '<' 输入重定向及 '&&' 链接写法；这两类错误发生在命令解析阶段。扩展批次的其他错误需要另行定位。",
            "Pi的powershell工具优先查找pwsh.exe，找不到则回退powershell.exe。初轮InvalidEndOfLine与旧版兼容性问题一致；新批次的根因不能直接套用初轮结论。",
            f"工具错误后出现同一工具成功调用的事件数：{sum(e['later_successful_same_tool'] is not None for e in report['events'])}/{report['tool_error_events']}；逐题是否最终通过见上表。",
            f"包含Unicode替代字符的错误输出：{sum(e['contains_replacement_characters'] for e in report['events'])}条；乱码原因待单独验证。",
            "直接作答且通过的题目可以没有工具调用；工具调用数为0本身不算异常。",
            "",
            "四、解释范围",
            f"当前已落盘{report['finalized_tasks']}/{n}题；没有观察到的失败类型应记录为未观察到，不能推断全量也不会出现。",
            f"本记录覆盖{n}道预选题；选题方法、范围和模型设置应与selection及harness清单一起解释。",
            "不同题目难度和解题长度不同，不能把耗时或Token差异全部归因于工具报错。",
            "summary.json的难度细分显示unknown；本记录从原始数据补回difficulty，后续统计也应保留该元数据。",
            "",
            "五、后续执行顺序",
            "1. 保留每个版本的原始日志和本记录，不覆盖结果。",
            "2. 原pilot-v1已发现PowerShell兼容性问题；harness-v2补充固定的环境说明，属于环境适配，不计入自进化效果。",
            "3. 用同样5题完成复核，确认完成率和正确率保持，并比较工具错误是否减少；修复效果以实际复核结果为准。",
            "4. 配置冻结后分批扩大基线。每批自动统计：未完成、API/Agent错误、超时、无代码、判题错误、错答/解题超限和可恢复工具错误。",
            "5. 所有比例注明分母：计划题数、已结束题数、工具调用数分别报告；中断和失败也保留，不能只统计成功题。",
            "6. 基线记录稳定后，再使用训练轨迹提炼技能，在相同且独立的test题目上做基线/技能版对照。",
        ]
    )
    (destination / "baseline-diagnosis.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", type=Path, default=ROOT / "results/baseline-5")
    parser.add_argument("--dataset", type=Path, default=ROOT / "selected-tasks.json")
    parser.add_argument("--output", type=Path, default=ROOT / "diagnosis-pilot-v1")
    args = parser.parse_args()
    report = audit(args.job_dir, args.dataset)
    write_report(report, args.output)
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ("records", "events")},
            ensure_ascii=False,
            indent=2,
        )
    )
