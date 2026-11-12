"""Chat clients with tool calling.

- ``ollama``: a local model through Ollama's native /api/chat. No key, code never leaves the machine.
- ``openai``: any OpenAI-compatible Chat Completions endpoint via OPENAI_API_KEY and OPENAI_BASE_URL.

Messages are kept in the OpenAI shape internally; the Ollama client converts on the way out.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

from . import net

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
DEFAULT_OPENAI_URL = "https://api.openai.com/v1"
DEFAULT_NUM_CTX = 32_768

Message = dict[str, Any]


class LLMError(RuntimeError):
    """The provider failed or returned something unusable."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Reply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ChatClient(Protocol):
    @property
    def name(self) -> str: ...

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> Reply: ...


class OllamaClient:
    def __init__(
        self,
        model: str = DEFAULT_OLLAMA_MODEL,
        base_url: str = DEFAULT_OLLAMA_URL,
        num_ctx: int = DEFAULT_NUM_CTX,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.num_ctx = num_ctx
        net.check_url(self.base_url)

    @property
    def name(self) -> str:
        return f"ollama:{self.model}"

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> Reply:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [_to_ollama(m) for m in messages],
            "stream": False,
            # Ollama's default context is small and it truncates silently, so set it explicitly.
            "options": {"temperature": temperature, "seed": 7, "num_ctx": self.num_ctx},
            "keep_alive": "30m",
        }
        if tools:
            payload["tools"] = tools
        if json_schema:
            payload["format"] = json_schema
        try:
            resp = net.post_json(f"{self.base_url}/api/chat", payload)
        except net.NetworkError as exc:
            raise LLMError(f"{exc}. Is `ollama serve` running and `{self.model}` pulled?") from exc
        msg = (resp or {}).get("message") or {}
        calls = [
            ToolCall(
                id=f"call_{i}",
                name=str((c.get("function") or {}).get("name", "")),
                arguments=_as_dict((c.get("function") or {}).get("arguments")),
            )
            for i, c in enumerate(msg.get("tool_calls") or [])
        ]
        content = str(msg.get("content") or "")
        if not calls and tools:
            calls = parse_text_tool_calls(content, {t["function"]["name"] for t in tools})
        return Reply(
            content=content,
            tool_calls=calls,
            prompt_tokens=int(resp.get("prompt_eval_count") or 0),
            completion_tokens=int(resp.get("eval_count") or 0),
        )


class OpenAICompatibleClient:
    def __init__(self, model: str, api_key: str, base_url: str = DEFAULT_OPENAI_URL) -> None:
        if not api_key:
            raise LLMError("OPENAI_API_KEY is not set")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        net.check_url(self.base_url)

    @property
    def name(self) -> str:
        return f"openai:{self.model}"

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> Reply:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "seed": 7,
            "messages": [_to_openai(m) for m in messages],
        }
        if tools:
            payload["tools"] = tools
        if json_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "greenbump_response", "schema": json_schema, "strict": True},
            }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            resp = net.post_json(f"{self.base_url}/chat/completions", payload, headers)
            msg = resp["choices"][0]["message"]
        except net.NetworkError as exc:
            raise LLMError(str(exc)) from exc
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("unexpected response shape from chat/completions") from exc
        calls = [
            ToolCall(
                id=str(c.get("id") or f"call_{i}"),
                name=str((c.get("function") or {}).get("name", "")),
                arguments=_as_dict((c.get("function") or {}).get("arguments")),
            )
            for i, c in enumerate(msg.get("tool_calls") or [])
        ]
        usage = resp.get("usage") or {}
        return Reply(
            content=str(msg.get("content") or ""),
            tool_calls=calls,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )


def build_client(provider: str, model: str | None = None, base_url: str | None = None) -> ChatClient:
    if provider == "ollama":
        return OllamaClient(
            model=model or os.getenv("GREENBUMP_MODEL") or DEFAULT_OLLAMA_MODEL,
            base_url=base_url or os.getenv("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_URL,
        )
    if provider == "openai":
        chosen = model or os.getenv("GREENBUMP_MODEL")
        if not chosen:
            raise LLMError("set --model or GREENBUMP_MODEL to a model your endpoint serves")
        return OpenAICompatibleClient(
            model=chosen,
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=base_url or os.getenv("OPENAI_BASE_URL") or DEFAULT_OPENAI_URL,
        )
    raise LLMError(f"unknown provider {provider!r}; use ollama or openai")


def parse_text_tool_calls(content: str, known: set[str]) -> list[ToolCall]:
    """Small models sometimes print a tool call as JSON text instead of using the API field."""
    decoder = json.JSONDecoder()
    calls: list[ToolCall] = []
    i = content.find("{")
    while i != -1:
        try:
            obj, end = decoder.raw_decode(content, i)
        except json.JSONDecodeError:
            i = content.find("{", i + 1)
            continue
        if isinstance(obj, dict) and obj.get("name") in known:
            args = obj.get("arguments", obj.get("parameters", {}))
            calls.append(ToolCall(id=f"text_{len(calls)}", name=str(obj["name"]), arguments=_as_dict(args)))
        i = content.find("{", end)
    return calls


def parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :] if "{" in text else text
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise LLMError("model did not return JSON") from None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError("model did not return valid JSON") from exc
    if not isinstance(data, dict):
        raise LLMError("model returned JSON that is not an object")
    return data


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {"_unparsed": value}
        return parsed if isinstance(parsed, dict) else {"_unparsed": value}
    return {}


def _to_ollama(m: Message) -> Message:
    if m["role"] == "assistant" and m.get("tool_calls"):
        return {
            "role": "assistant",
            "content": m.get("content") or "",
            "tool_calls": [
                {
                    "function": {
                        "name": c["function"]["name"],
                        "arguments": _as_dict(c["function"]["arguments"]),
                    }
                }
                for c in m["tool_calls"]
            ],
        }
    if m["role"] == "tool":
        return {"role": "tool", "content": m["content"], "tool_name": m.get("name", "")}
    return {"role": m["role"], "content": m.get("content") or ""}


def _to_openai(m: Message) -> Message:
    if m["role"] == "tool":
        return {"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]}
    return m
