"""Phase 1: gather the facts about a broken upgrade. No LLM is involved here.

The output is a "case file": which packages moved, how the tests fail, which files use the
package, and the changelog passages that best match the errors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .changelog import ChangelogIndex, Passage, render_passages
from .guardrails import is_test_file, package_aliases
from .models import Bump, TestRun
from .workspace import Workspace

_IDENT_PATTERNS = [
    re.compile(r"has no attribute '(\w+)'"),
    re.compile(r"cannot import name '(\w+)'"),
    re.compile(r"No module named '([\w.]+)'"),
    re.compile(r"unexpected keyword argument '(\w+)'"),
    re.compile(r"`([A-Za-z_][\w.]*(?:\(\))?)`"),
]
_EXC_RE = re.compile(r"\b([A-Z]\w*(?:Error|Exception|Warning))\b")
_IMPORT_FROM_RE = re.compile(r"cannot import name '\w+' from '([\w.]+)'")
_PAREN_PATH_RE = re.compile(r"\s*\([^)]*[/\\][^)]*\)")
_GENERIC = {
    "AssertionError",
    "Exception",
    "TypeError",
    "ValueError",
    "AttributeError",
    "ImportError",
    "KeyError",
    "RuntimeError",
    "ModuleNotFoundError",
    "NameError",
    "IndexError",
    "Warning",
    "UserWarning",
    "DeprecationWarning",
}


@dataclass
class CaseFile:
    bumps: list[Bump]
    tests: TestRun
    files: dict[str, str]
    other_usages: dict[str, list[tuple[int, str]]]
    passages: list[Passage]
    queries: list[str]
    warnings: list[str] = field(default_factory=list)

    def render(self, max_test_chars: int = 7000) -> str:
        out = ["## Upgrade", *(f"- {b.describe()}" for b in self.bumps), ""]
        out += [
            f"## Test run after the upgrade: {self.tests.headline()}",
            "```text",
            truncate_middle(self.tests.output.strip(), max_test_chars),
            "```",
            "",
        ]
        if self.files:
            out.append("## Files that import the upgraded package(s), with line numbers")
            for rel_path, text in self.files.items():
                out += [f"### {rel_path}", "```python", number_lines(text), "```", ""]
        if self.other_usages:
            out.append("## More usages (files too large to include; use read_file)")
            for rel_path, hits in self.other_usages.items():
                out += [f"### {rel_path}", *(f"{n:>5} | {line}" for n, line in hits), ""]
        out += [
            "## Upstream notes that may be relevant",
            f"Search queries used: {', '.join(self.queries) or '(none)'}",
            "",
            render_passages(self.passages),
        ]
        return "\n".join(out)


def build_case(
    ws: Workspace,
    bumps: list[Bump],
    tests: TestRun,
    index: ChangelogIndex,
    warnings: list[str] | None = None,
    file_budget: int = 24_000,
    max_passages: int = 8,
) -> CaseFile:
    sources = ws.snapshot()
    import_names = {b.import_name for b in bumps}
    using = [
        p for p in sorted(sources) if p.endswith(".py") and package_aliases({p: sources[p]}, import_names)
    ]
    using.sort(key=is_test_file)

    files: dict[str, str] = {}
    other: dict[str, list[tuple[int, str]]] = {}
    used = 0
    for rel_path in using:
        text = sources[rel_path]
        if used + len(text) <= file_budget:
            files[rel_path] = text
            used += len(text)
        else:
            aliases = package_aliases({rel_path: text}, import_names)
            other[rel_path] = usage_lines(text, aliases)

    queries = error_queries(tests.output, bumps)
    passages: list[Passage] = []
    seen: set[tuple[str, int]] = set()
    for query in queries:
        for p in index.search(query, k=2):
            if (p.url, p.line) not in seen and len(passages) < max_passages:
                seen.add((p.url, p.line))
                passages.append(p)
    return CaseFile(bumps, tests, files, other, passages, queries, list(warnings or []))


def error_queries(output: str, bumps: list[Bump], limit: int = 8) -> list[str]:
    """Search terms pulled from the failure output: removed names, exception types, error lines."""
    found: list[str] = []
    for pattern in _IDENT_PATTERNS:
        found += pattern.findall(output)
    found += [e for e in _EXC_RE.findall(output) if e not in _GENERIC]
    # Release notes often deprecate a whole module without naming each function in it.
    found += [f"{module} module deprecated" for module in _IMPORT_FROM_RE.findall(output) if "." in module]
    skip = {b.import_name for b in bumps} | {b.package for b in bumps}
    error_lines = [
        _PAREN_PATH_RE.sub("", line[1:]).strip()[:120]
        for line in output.splitlines()
        if line.startswith("E ") and len(line.strip()) > 8
    ]
    queries: list[str] = []
    for q in [*found, *error_lines]:
        q = q.strip()
        short = q.split(".")[-1] if "." in q and " " not in q else q
        if short and short not in skip and short not in queries:
            queries.append(short)
        if len(queries) >= limit:
            break
    return queries


def usage_lines(text: str, aliases: set[str], limit: int = 40) -> list[tuple[int, str]]:
    if not aliases:
        return []
    pattern = re.compile(r"\b(" + "|".join(re.escape(a) for a in sorted(aliases)) + r")\b")
    hits = [(n, line.rstrip()) for n, line in enumerate(text.splitlines(), 1) if pattern.search(line)]
    return hits[:limit]


def number_lines(text: str, start: int = 1) -> str:
    return "\n".join(f"{n:>5} | {line}" for n, line in enumerate(text.splitlines(), start))


def truncate_middle(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = limit // 3
    tail = limit - head
    return f"{text[:head]}\n... [{len(text) - limit} characters cut] ...\n{text[-tail:]}"
