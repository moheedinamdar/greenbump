"""The tools the agent may call. This list is the agent's entire reach.

Read tools are free. ``edit_file`` only touches the throwaway work copy and runs the guardrails
first. ``run_tests`` executes code, so it runs in a child process with a scrubbed environment.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any

from .changelog import ChangelogIndex, render_passages
from .context import error_queries, number_lines, truncate_middle
from .guardrails import check_edit, protected_reason
from .models import Bump, TestRun
from .runner import run_pytest
from .workspace import Workspace, WorkspaceError

MAX_TOOL_OUTPUT = 8000


def _spec(name: str, description: str, props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


_STR = {"type": "string"}
_INT = {"type": "integer"}

TOOL_SPECS = [
    _spec("list_files", "List the Python files in the repository.", {}, []),
    _spec(
        "read_file",
        "Read a file. Output has line numbers. Use start_line and end_line for long files.",
        {"path": _STR, "start_line": _INT, "end_line": _INT},
        ["path"],
    ),
    _spec(
        "search_code",
        "Find lines that contain a piece of text (plain text, not regex).",
        {"text": _STR},
        ["text"],
    ),
    _spec(
        "search_changelog",
        "Search the upstream changelog and migration notes of the upgraded package(s).",
        {"query": _STR},
        ["query"],
    ),
    _spec(
        "edit_file",
        "Replace old_text with new_text in a file. old_text must match the file exactly, including "
        "indentation, without line-number prefixes. It must be unique unless replace_all is true.",
        {"path": _STR, "old_text": _STR, "new_text": _STR, "replace_all": {"type": "boolean"}},
        ["path", "old_text", "new_text"],
    ),
    _spec("run_tests", "Run the test suite and show the result.", {}, []),
    _spec(
        "finish",
        "Call this when all tests pass. Summarise each change and why the new version needed it.",
        {"summary": _STR},
        ["summary"],
    ),
    _spec(
        "give_up",
        "Call this when you cannot fix the upgrade safely. Explain what you found.",
        {"reason": _STR},
        ["reason"],
    ),
]
TOOL_NAMES = {t["function"]["name"] for t in TOOL_SPECS}


@dataclass
class ToolResult:
    text: str
    terminal: str | None = None  # "finish" or "give_up" ends the loop
    summary: str = ""


@dataclass
class Toolbox:
    ws: Workspace
    python: str
    index: ChangelogIndex
    bumps: list[Bump]
    test_timeout: float = 180.0
    test_runs: list[TestRun] = field(default_factory=list)
    edits_applied: int = 0
    edits_refused: int = 0
    guardrail_hits: list[str] = field(default_factory=list)

    def call(self, name: str, args: dict[str, Any]) -> ToolResult:
        if name not in TOOL_NAMES:
            return ToolResult(f"ERROR: unknown tool {name!r}. Available: {', '.join(sorted(TOOL_NAMES))}")
        if "_unparsed" in args:
            return ToolResult("ERROR: the tool arguments were not valid JSON. Send a JSON object.")
        try:
            result: ToolResult = getattr(self, f"_{name}")(args)
        except (WorkspaceError, KeyError, TypeError, ValueError) as exc:
            return ToolResult(f"ERROR: {exc}")
        result.text = truncate_middle(result.text, MAX_TOOL_OUTPUT)
        return result

    def _list_files(self, _args: dict[str, Any]) -> ToolResult:
        return ToolResult("\n".join(self.ws.python_files()) or "(no Python files)")

    def _read_file(self, args: dict[str, Any]) -> ToolResult:
        lines = self.ws.read(str(args["path"])).splitlines()
        start = max(1, int(args.get("start_line") or 1))
        end = min(len(lines), int(args.get("end_line") or start + 299))
        if not lines:
            return ToolResult("(empty file)")
        body = number_lines("\n".join(lines[start - 1 : end]), start)
        more = f"\n[lines {end + 1}-{len(lines)} not shown]" if end < len(lines) else ""
        return ToolResult(body + more)

    def _search_code(self, args: dict[str, Any]) -> ToolResult:
        needle = str(args["text"])
        if not needle:
            raise ValueError("text must not be empty")
        hits = []
        for rel_path, text in self.ws.snapshot().items():
            if not rel_path.endswith(".py"):
                continue
            hits += [
                f"{rel_path}:{n}: {line.strip()}"
                for n, line in enumerate(text.splitlines(), 1)
                if needle in line
            ]
        return ToolResult(
            "\n".join(hits[:60]) + ("\n[more hits not shown]" if len(hits) > 60 else "") or "(no matches)"
        )

    def _search_changelog(self, args: dict[str, Any]) -> ToolResult:
        if not len(self.index):
            return ToolResult("No changelog is available for this upgrade. Rely on the error messages.")
        return ToolResult(render_passages(self.index.search(str(args["query"]), k=4)))

    def _edit_file(self, args: dict[str, Any]) -> ToolResult:
        rel_path = str(args["path"])
        reason = protected_reason(rel_path)
        if reason:
            self.edits_refused += 1
            self.guardrail_hits.append(f"[protected-file] {rel_path}")
            return ToolResult(f"REFUSED: {reason}. Change the application code to use the new API instead.")
        old, new = str(args["old_text"]), str(args["new_text"])
        if old == new:
            raise ValueError("new_text is identical to old_text, so this edit changes nothing")
        before = self.ws.read(rel_path)
        count = self.ws.replace(rel_path, old, new, bool(args.get("replace_all", False)))
        after = self.ws.read(rel_path)
        if rel_path.endswith(".py"):
            try:
                ast.parse(after)
            except SyntaxError as exc:
                self.ws.write(rel_path, before)
                raise ValueError(
                    f"edit rolled back: it makes {rel_path} invalid Python (line {exc.lineno}: {exc.msg})"
                ) from None
        violations = check_edit(rel_path, before, after, {b.import_name for b in self.bumps})
        if violations:
            self.ws.write(rel_path, before)
            self.edits_refused += 1
            self.guardrail_hits += [str(v) for v in violations]
            return ToolResult(
                "REFUSED and rolled back. The edit breaks these rules:\n"
                + "\n".join(f"- {v.rule}: {v.detail}" for v in violations)
                + "\nFix the code properly with the new API of the library."
            )
        self.edits_applied += 1
        notes = [
            f"Note: `{name}` is no longer imported in {rel_path} but the file still uses it."
            for name in sorted(_imported(before) - _imported(after))
            if name in _used_names(after)
        ]
        return ToolResult(
            "\n".join(
                [
                    f"OK: replaced {count} occurrence(s) in {rel_path}. The file now reads:",
                    _excerpt(after, new),
                    *notes,
                ]
            )
        )

    def _run_tests(self, _args: dict[str, Any]) -> ToolResult:
        return ToolResult(self.describe_run(self.run_tests()))

    def _finish(self, args: dict[str, Any]) -> ToolResult:
        run = self.run_tests()
        if not run.ok:
            return ToolResult("Not finished: the tests still fail. Keep fixing.\n\n" + self.describe_run(run))
        return ToolResult("Finished.", terminal="finish", summary=str(args.get("summary", "")))

    def _give_up(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult("Stopped.", terminal="give_up", summary=str(args.get("reason", "")))

    def run_tests(self) -> TestRun:
        self.ws.clear_bytecode()
        run = run_pytest(self.ws.root, self.python, self.test_timeout)
        self.test_runs.append(run)
        return run

    def describe_run(self, run: TestRun) -> str:
        """Test result plus changelog passages for the NEW errors, since fixing one error reveals the next."""
        if run.ok:
            return f"Result: {run.headline()}. All tests pass. Call finish."
        key_lines = list(dict.fromkeys(line for line in run.output.splitlines() if line.startswith("E ")))[:8]
        parts = [f"Result: {run.headline()}"]
        if key_lines:
            parts += ["", "Key error lines:", *key_lines]
        if len(self.index):
            passages = []
            for query in error_queries(run.output, self.bumps, limit=4):
                passages += [p for p in self.index.search(query, k=1) if p not in passages]
            if passages:
                parts += ["", "Changelog passages matching these errors:", render_passages(passages[:3])]
        parts += ["", "Full output:", truncate_middle(run.output.strip(), 2500)]
        return "\n".join(parts)


def _excerpt(text: str, new: str, context: int = 3) -> str:
    """The edited region with line numbers, so the model sees what its edit really did."""
    lines = text.splitlines()
    start = text[: text.find(new)].count("\n") if new and new in text else 0
    end = start + max(1, new.count("\n") + 1)
    lo, hi = max(0, start - context), min(len(lines), end + context)
    return number_lines("\n".join(lines[lo:hi]), lo + 1)


def _imported(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update((a.asname or a.name).split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(a.asname or a.name for a in node.names)
    return names


def _used_names(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
