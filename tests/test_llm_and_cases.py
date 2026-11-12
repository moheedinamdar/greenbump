from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from greenbump import llm, net
from greenbump.evals import load_cases
from greenbump.llm import LLMError, OllamaClient, parse_json_object, parse_text_tool_calls
from greenbump.models import Bump

CASES = Path(__file__).resolve().parents[1] / "evals" / "cases"


def test_text_tool_calls_are_recovered() -> None:
    content = 'Sure.\n<tool_call>\n{"name": "read_file", "arguments": {"path": "a.py"}}\n</tool_call>'
    calls = parse_text_tool_calls(content, {"read_file"})
    assert [(c.name, c.arguments) for c in calls] == [("read_file", {"path": "a.py"})]
    assert parse_text_tool_calls('{"name": "rm_rf", "arguments": {}}', {"read_file"}) == []


def test_parse_json_object_handles_fences() -> None:
    assert parse_json_object('```json\n{"edits": [], "summary": "s"}\n```') == {"edits": [], "summary": "s"}
    with pytest.raises(LLMError):
        parse_json_object("no json here")


def test_ollama_payload_and_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, Any] = {}

    def fake_post(url: str, payload: dict[str, Any], headers: Any = None, timeout: float = 0) -> Any:
        sent.update(payload)
        return {
            "message": {"content": "", "tool_calls": [{"function": {"name": "run_tests", "arguments": {}}}]},
            "prompt_eval_count": 120,
            "eval_count": 7,
        }

    monkeypatch.setattr(net, "post_json", fake_post)
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": '{"path": "a.py"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "c1", "name": "read_file", "content": "1 | x"},
    ]
    reply = OllamaClient().chat(messages, tools=[{"type": "function", "function": {"name": "run_tests"}}])
    assert reply.tool_calls[0].name == "run_tests"
    assert (reply.prompt_tokens, reply.completion_tokens) == (120, 7)
    assert sent["options"]["num_ctx"] == llm.DEFAULT_NUM_CTX
    assert sent["messages"][1]["tool_calls"][0]["function"]["arguments"] == {"path": "a.py"}
    assert sent["messages"][2] == {"role": "tool", "content": "1 | x", "tool_name": "read_file"}


def test_build_client_validation() -> None:
    with pytest.raises(LLMError):
        llm.build_client("nope")


def test_bump_parse() -> None:
    assert Bump.parse("pydantic:1.10.27:2.14.3") == Bump("pydantic", "2.14.3", "1.10.27")
    assert Bump.parse("numpy:2.5.4").from_version is None
    assert Bump("PyYAML", "6.0").import_name == "yaml"
    assert Bump("scikit-learn", "1.0").import_name == "sklearn"
    with pytest.raises(ValueError):
        Bump.parse("pydantic")


def test_shipped_eval_cases_load() -> None:
    cases = load_cases(CASES)
    assert len(cases) >= 6
    for case in cases:
        assert case.bumps and case.changelog_urls, case.name
        assert (case.repo / "requirements.txt").is_file(), case.name
        assert any(case.solution.rglob("*.py")), case.name
