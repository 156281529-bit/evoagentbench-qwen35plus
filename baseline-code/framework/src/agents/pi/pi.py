"""Pi 1.5 print-mode adapter for isolated code-implementation trials."""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from agents.base import AgentAdapter, C_MAGENTA, C_RESET
from config import get_config, register_agent


class PiAdapter(AgentAdapter):
    name = "pi"

    def __init__(self):
        self._temp_workspace = None

    def _ensure_temp_config(self):
        if self._temp_workspace:
            return
        root = Path(tempfile.mkdtemp(prefix="evoagentbench-pi-"))
        self._temp_workspace = str(root)
        (root / "sessions").mkdir()
        (root / "workspace").mkdir()
        agent_dir = root / "agent"
        agent_dir.mkdir()
        env = super()._get_subprocess_env() or os.environ
        source = Path(env.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent"))
        # Reuse provider definitions/credentials, but never personal sessions,
        # settings, extensions, skills, or project instructions.
        for filename in ("models.json", "auth.json"):
            if (source / filename).is_file():
                shutil.copy2(source / filename, agent_dir / filename)

    def _cleanup_temp_config(self):
        if self._temp_workspace:
            shutil.rmtree(self._temp_workspace, ignore_errors=True)
        self._temp_workspace = None

    def setup_mcp(self, mcp_servers, disabled_tools=None):
        if mcp_servers:
            raise NotImplementedError("Pi adapter currently supports non-MCP domains")

    def teardown_mcp(self):
        self._cleanup_temp_config()

    def _session_dir(self):
        self._ensure_temp_config()
        return Path(self._temp_workspace) / "sessions"

    def _session_file(self, session_id):
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id)
        return self._session_dir() / f"{safe_id}.jsonl"

    def _cli_prefix(self):
        command = self._command()
        executable = Path(shutil.which(command) or command)
        if executable.suffix.lower() in (".cmd", ".bat"):
            # Avoid cmd.exe: prompts may contain quotes, %, &, or newlines.
            entry = (
                executable.parent
                / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
            )
            if not entry.is_file():
                raise FileNotFoundError(
                    "Cannot resolve Pi npm launcher; set command to Pi's cli.js"
                )
            executable = entry
        if executable.suffix.lower() in (".js", ".mjs"):
            local_node = executable.parent / "node.exe"
            node = str(local_node) if local_node.is_file() else shutil.which("node")
            if not node:
                raise FileNotFoundError("Node.js is required to run Pi")
            return [node, str(executable)]
        return [str(executable)]

    def _build_cli_cmd(self, prompt, session_id, timeout):
        cfg = get_config().get("agent", {})
        cmd = self._cli_prefix() + [
            "--print",
            "--mode",
            "text",
            "--session",
            str(self._session_file(session_id)),
            "--no-extensions",
            "--no-skills",
            "--no-prompt-templates",
            "--no-context-files",
            "--no-mcp",
        ]
        for key in ("provider", "model"):
            if cfg.get(key):
                cmd.extend([f"--{key}", str(cfg[key])])
        if cfg.get("reasoningEffort"):
            cmd.extend(["--thinking", str(cfg["reasoningEffort"])])
        tools = cfg.get("tools")
        if tools is None:
            shell = "powershell" if os.name == "nt" else "bash"
            tools = [shell, "read", "write", "edit", "grep", "find", "ls"]
        if isinstance(tools, list):
            tools = ",".join(tools)
        if not isinstance(tools, str):
            raise ValueError("Pi tools must be a list or comma-separated string")
        cmd.extend(["--tools", tools] if tools else ["--no-tools"])
        # The full prompt goes over stdin, avoiding Windows' command-line limit.
        return cmd

    def _get_subprocess_env(self):
        self._ensure_temp_config()
        env = super()._get_subprocess_env() or os.environ.copy()
        env["PI_CODING_AGENT_DIR"] = str(Path(self._temp_workspace) / "agent")
        env["PI_OFFLINE"] = "1"
        env["PI_TELEMETRY"] = "0"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["PATH"] = (
            str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
        )
        return env

    @staticmethod
    def _kill_process_tree(process):
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                timeout=10,
                check=False,
            )
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.poll() is None:
            process.kill()

    def call_agent(self, prompt, session_id, timeout=3600, cwd=None):
        self._ensure_temp_config()
        start = time.monotonic()
        result = {"response": "", "completion_status": "error", "method": "cli"}
        try:
            cmd = self._build_cli_cmd(prompt, session_id, timeout)
            with subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=self._get_subprocess_env(),
                cwd=cwd or str(Path(self._temp_workspace) / "workspace"),
                start_new_session=os.name != "nt",
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt"
                else 0,
            ) as process:
                try:
                    stdout, stderr = process.communicate(input=prompt, timeout=timeout)
                    result["completion_status"] = (
                        "completed" if process.returncode == 0 else "error"
                    )
                except subprocess.TimeoutExpired:
                    self._kill_process_tree(process)
                    stdout, stderr = process.communicate(timeout=10)
                    result["completion_status"] = "timeout"
                    result["error"] = f"Pi timed out after {timeout}s"
                result.update(
                    response=stdout,
                    returncode=process.returncode,
                    stderr=stderr[:2000] or None,
                )
        except (OSError, ValueError) as exc:
            result["error"] = str(exc)
        result["elapsed_sec"] = round(time.monotonic() - start, 1)
        return result

    def _parse_watch_record(self, rec, ts, prefix):
        msg = rec.get("message", {}) if rec.get("type") == "message" else {}
        if msg.get("role") == "assistant":
            for part in msg.get("content", []):
                if part.get("type") == "thinking":
                    text = part.get("thinking", "").strip().split("\n")[0][:120]
                    if text:
                        print(f"  {C_MAGENTA}{ts} {prefix} {text}{C_RESET}", flush=True)
                if part.get("type") == "toolCall":
                    args = part.get("arguments", {})
                    self._print_tool_call(ts, prefix, f"{part.get('name')}({args})")
        if msg.get("role") == "toolResult":
            text = "\n".join(p.get("text", "") for p in msg.get("content", []))
            self._print_tool_output(ts, prefix, text)

    def _parse_session_entry(self, entry, stats):
        if entry.get("type") != "message":
            return
        msg = entry.get("message", {})
        if msg.get("role") == "assistant":
            stats["turns"] += 1
            usage = msg.get("usage", {})
            for key in ("input", "output", "cacheRead", "cacheWrite", "reasoning"):
                stats[key] = stats.get(key, 0) + (usage.get(key) or 0)
            stats["total"] += usage.get("totalTokens") or sum(
                usage.get(key, 0) or 0
                for key in ("input", "output", "cacheRead", "cacheWrite")
            )
            stats["last_stop_reason"] = msg.get("stopReason")
            if msg.get("stopReason") == "error":
                stats["provider_error_count"] = stats.get("provider_error_count", 0) + 1
            calls = sum(p.get("type") == "toolCall" for p in msg.get("content", []))
            stats["tool_call_count"] = stats.get("tool_call_count", 0) + calls
        elif msg.get("role") == "toolResult":
            key = "tool_error_count" if msg.get("isError") else "tool_success_count"
            stats[key] = stats.get(key, 0) + 1

    def collect_session(self, session_id, trial_dir):
        # Explicit UTF-8 also handles Chinese in Windows' legacy locales.
        stats = {
            "turns": 0,
            "input": 0,
            "output": 0,
            "total": 0,
            "last_stop_reason": None,
        }
        source = self._session_file(session_id)
        if source.is_file():
            shutil.copy2(source, Path(trial_dir) / "session.jsonl")
            with source.open(encoding="utf-8") as stream:
                for line in stream:
                    try:
                        self._parse_session_entry(json.loads(line), stats)
                    except json.JSONDecodeError:
                        continue
        return stats

    def should_retry(self, result):
        if result.get("verifier_result", {}).get("reward", 0) > 0:
            return None
        agent = result.get("agent_result", {})
        if agent.get("completion_status") == "timeout":
            return None
        usage = result.get("token_usage", {})
        if (
            usage.get("last_stop_reason") == "error"
            or result.get("last_stop_reason") == "error"
        ):
            return "provider_error"
        if agent.get("completion_status") == "completed" and usage.get("turns", 0) == 0:
            return "zero_turns"
        return super().should_retry(result)


register_agent("pi", PiAdapter)
