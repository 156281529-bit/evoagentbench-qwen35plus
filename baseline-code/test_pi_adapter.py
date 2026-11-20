"""Pi process transport, isolation, accounting, and retry contracts."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import config
from agents.pi.pi import PiAdapter


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    source = tmp_path / "personal"
    source.mkdir()
    (source / "models.json").write_text('{"providers": {}}', encoding="utf-8")
    (source / "settings.json").write_text('{"skills": ["private"]}')
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(source))
    monkeypatch.setattr(
        config,
        "_config",
        {"agent": {"name": "pi", "model": "qwen3.5-plus", "provider": "thingo"}},
    )
    agent = PiAdapter()
    yield agent
    agent._cleanup_temp_config()


def test_isolated_workspace_and_credentials(adapter):
    adapter._ensure_temp_config()
    root = Path(adapter._temp_workspace)
    assert (root / "workspace").is_dir()
    assert (root / "agent/models.json").is_file()
    assert not (root / "agent/settings.json").exists()
    env = adapter._get_subprocess_env()
    assert env["PI_CODING_AGENT_DIR"] == str(root / "agent")
    assert adapter._session_file("a:b").parent == root / "sessions"
    other = PiAdapter()
    try:
        assert other._session_file("a:b") != adapter._session_file("a:b")
    finally:
        other._cleanup_temp_config()


def test_cli_keeps_prompt_off_command_line(adapter, monkeypatch):
    monkeypatch.setattr(adapter, "_cli_prefix", lambda: ["pi"])
    cmd = adapter._build_cli_cmd("secret prompt & % PATH", "test", 10)
    assert "secret prompt & % PATH" not in cmd
    assert cmd[cmd.index("--provider") + 1] == "thingo"
    assert "--no-skills" in cmd
    assert "--no-context-files" in cmd


def test_windows_npm_launcher_uses_node(adapter, monkeypatch, tmp_path):
    launcher = tmp_path / "pi.cmd"
    launcher.touch()
    entry = tmp_path / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
    entry.parent.mkdir(parents=True)
    entry.touch()
    monkeypatch.setattr(adapter, "_command", lambda: str(launcher))
    monkeypatch.setattr(
        "agents.pi.pi.shutil.which",
        lambda cmd: "node.exe" if cmd == "node" else str(launcher),
    )
    assert adapter._cli_prefix() == ["node.exe", str(entry)]


def test_long_unicode_stdin_and_cwd(adapter, monkeypatch):
    script = "import os,sys,json; print(json.dumps([sys.stdin.read(),os.getcwd()],ensure_ascii=False))"
    monkeypatch.setattr(
        adapter, "_build_cli_cmd", lambda *args: [sys.executable, "-c", script]
    )
    prompt = '中文 & %PATH% "quotes"\n' * 3000
    result = adapter.call_agent(prompt, "transport", timeout=10)
    assert result["completion_status"] == "completed"
    text, cwd = json.loads(result["response"])
    assert text == prompt
    assert Path(cwd) == Path(adapter._temp_workspace) / "workspace"


def test_timeout_and_partial_output(adapter, monkeypatch):
    script = "import time; print('partial',flush=True); time.sleep(30)"
    monkeypatch.setattr(
        adapter, "_build_cli_cmd", lambda *args: [sys.executable, "-c", script]
    )
    result = adapter.call_agent("test", "timeout", timeout=0.5)
    assert result["completion_status"] == "timeout"
    assert "partial" in result["response"]


def test_collection_and_token_usage(adapter, tmp_path):
    source = adapter._session_file("stats")
    entries = [
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "toolCall"}],
                "usage": {"input": 3, "output": 4, "cacheRead": 5, "totalTokens": 12},
                "stopReason": "toolUse",
            },
        },
        {
            "type": "message",
            "message": {
                "role": "toolResult",
                "isError": True,
                "content": [{"type": "text", "text": "中文"}],
            },
        },
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [],
                "usage": {"input": 2, "output": 1},
                "stopReason": "stop",
            },
        },
    ]
    source.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n{partial",
        encoding="utf-8",
    )
    usage = adapter.collect_session("stats", tmp_path)
    assert usage["turns"] == 2
    assert usage["input"] == 5
    assert usage["output"] == 5
    assert usage["total"] == 15
    assert usage["tool_error_count"] == 1
    assert usage["tool_call_count"] == 1
    assert usage["last_stop_reason"] == "stop"
    assert (tmp_path / "session.jsonl").read_bytes() == source.read_bytes()


@pytest.mark.parametrize(
    "completion,turns,reward,stop,expected",
    [
        ("completed", 1, 0, "stop", None),
        ("completed", 0, 0, None, "zero_turns"),
        ("error", 1, 0, "error", "provider_error"),
        ("error", 1, 1, "error", None),
        ("timeout", 0, 0, None, None),
    ],
)
def test_retry_policy(adapter, completion, turns, reward, stop, expected):
    result = {
        "agent_result": {"completion_status": completion},
        "token_usage": {"turns": turns},
        "last_stop_reason": stop,
        "verifier_result": {"reward": reward},
    }
    assert adapter.should_retry(result) == expected
