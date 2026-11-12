from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from greenbump.llm import Message, Reply, ToolCall

APP = "def double(x):\n    return x * 3\n"
TEST = "from app import double\n\n\ndef test_double():\n    assert double(2) == 4\n"


@pytest.fixture
def mini_repo(tmp_path: Path) -> Path:
    """A repo whose single test fails until ``* 3`` becomes ``* 2``."""
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "app.py").write_text(APP)
    (repo / "tests" / "test_app.py").write_text(TEST)
    (repo / "requirements.txt").write_text("fakelib==2.0\n")
    (repo / "pytest.ini").write_text("[pytest]\ntestpaths = tests\npythonpath = .\n")
    (repo / ".venv").mkdir()
    (repo / ".venv" / "junk.txt").write_text("ignored")
    return repo


@pytest.fixture
def python() -> str:
    return sys.executable


class ScriptedClient:
    """Replays a fixed list of tool calls, so agent tests need no model and no network."""

    def __init__(self, script: list[tuple[str, dict[str, Any]]] | None = None, content: str = "") -> None:
        self.script = list(script or [])
        self.content = content
        self.seen: list[list[Message]] = []
        self.temperatures: list[float] = []

    @property
    def name(self) -> str:
        return "scripted"

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> Reply:
        self.seen.append(messages)
        self.temperatures.append(temperature)
        if json_schema is not None:
            return Reply(content=self.content, prompt_tokens=10, completion_tokens=5)
        if not self.script:
            return Reply(content="I am thinking", prompt_tokens=1, completion_tokens=1)
        name, args = self.script.pop(0)
        return Reply(
            content="",
            tool_calls=[ToolCall(f"c{len(self.seen)}", name, args)],
            prompt_tokens=10,
            completion_tokens=5,
        )


@pytest.fixture
def no_changelog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("greenbump.fixer.load_docs", lambda *a, **k: ([], []))
