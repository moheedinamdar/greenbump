"""Rules that stop the agent from "fixing" an upgrade by cheating.

Every rule compares the file before and after, so a pattern that was already in the code
is not blamed on the agent. Only new occurrences count.
"""

from __future__ import annotations

import ast
import difflib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

PROTECTED_BASENAMES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "pytest.ini",
    "tox.ini",
    "noxfile.py",
    "conftest.py",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "uv.lock",
    "pdm.lock",
    ".python-version",
    "Makefile",
}
PROTECTED_PATTERNS = [
    re.compile(r"(^|/)requirements[^/]*\.(txt|in)$"),
    re.compile(r"(^|/)constraints[^/]*\.txt$"),
    re.compile(r"(^|/)\.github/"),
    re.compile(r"\.lock$"),
]
FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "skips-tests",
        re.compile(
            r"\bpytest\.(skip|importorskip)\b|\bpytest\.mark\.(skip|skipif|xfail)\b|\bunittest\.skip|@skip\b"
        ),
    ),
    (
        "silences-warnings",
        re.compile(r"\bfilterwarnings\b|\bwarnings\.(simplefilter|filterwarnings)\b|\bcatch_warnings\b"),
    ),
    ("suppression-comment", re.compile(r"#\s*type:\s*ignore|#\s*noqa|#\s*pragma:\s*no cover")),
    ("swallows-errors", re.compile(r"^\s*except\s*:|^\s*except\s+BaseException\b", re.MULTILINE)),
    (
        "process-or-network",
        re.compile(
            r"\bsubprocess\b|\bos\.(system|popen|exec\w*|spawn\w*)\b|\bsocket\b|\burllib\.request\b|\burlopen\b"
            r"|\brequests\.(get|post|put|patch|delete|request|Session)\b|\bhttpx\b|\bhttp\.client\b"
        ),
    ),
    (
        "dynamic-code",
        re.compile(
            r"\beval\(|\bexec\(|\b__import__\(|\bimportlib\b|\bsys\.modules\b|\bsetattr\(|\bbuiltins\b"
        ),
    ),
]


@dataclass(frozen=True)
class Violation:
    rule: str
    path: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.rule}] {self.path}: {self.detail}"


@dataclass(frozen=True)
class Limits:
    max_files: int = 10
    max_changed_lines: int = 200


def protected_reason(rel_path: str) -> str | None:
    name = PurePosixPath(rel_path).name
    if name in PROTECTED_BASENAMES:
        return f"{name} controls dependencies, CI or the test run, and is off limits"
    for pattern in PROTECTED_PATTERNS:
        if pattern.search(rel_path):
            return "dependency, lock and CI files are off limits (no downgrades or pin changes)"
    return None


def is_test_file(rel_path: str) -> bool:
    p = PurePosixPath(rel_path)
    return p.suffix == ".py" and (
        p.name.startswith("test_") or p.name.endswith("_test.py") or "tests" in p.parts
    )


def package_aliases(sources: dict[str, str], import_names: Iterable[str]) -> set[str]:
    """Names bound to the upgraded packages or objects imported from them, e.g. ``np`` or ``Markup``."""
    wanted = set(import_names)
    aliases: set[str] = set()

    def matches(module: str) -> bool:
        return any(module == w or module.startswith(w + ".") for w in wanted)

    for rel_path, text in sources.items():
        if not rel_path.endswith(".py"):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if matches(alias.name):
                        aliases.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module and matches(node.module):
                aliases.update(a.asname or a.name for a in node.names if a.name != "*")
    return aliases


def monkeypatch_pattern(aliases: set[str]) -> re.Pattern[str] | None:
    if not aliases:
        return None
    names = "|".join(sorted(re.escape(a) for a in aliases))
    return re.compile(rf"^\s*(?:{names})(?:\.\w+)+\s*(?:=(?!=)|\+=)", re.MULTILINE)


def check_changes(
    original: dict[str, str],
    current: dict[str, str],
    import_names: Iterable[str],
    limits: Limits | None = None,
) -> list[Violation]:
    """Compare two snapshots of the repository and list every rule the change breaks."""
    limits = limits or Limits()
    violations: list[Violation] = []
    changed = sorted(p for p in set(original) | set(current) if original.get(p) != current.get(p))
    patch_rule = monkeypatch_pattern(package_aliases({**original, **current}, import_names))
    changed_lines = 0

    for rel_path in changed:
        before, after = original.get(rel_path), current.get(rel_path)
        reason = protected_reason(rel_path)
        if reason:
            violations.append(Violation("protected-file", rel_path, reason))
        if after is None:
            violations.append(Violation("deleted-file", rel_path, "files may not be deleted"))
            continue
        if before is None:
            violations.append(Violation("new-file", rel_path, "files may not be created"))
            before = ""
        changed_lines += _changed_line_count(before, after)
        rules = list(FORBIDDEN_PATTERNS)
        if patch_rule is not None:
            rules.append(("patches-library", patch_rule))
        for rule, pattern in rules:
            added = len(pattern.findall(after)) - len(pattern.findall(before))
            if added > 0:
                violations.append(
                    Violation(rule, rel_path, f"adds {added} occurrence(s) of /{pattern.pattern}/")
                )
        if is_test_file(rel_path):
            violations.extend(_test_integrity(rel_path, before, after))

    if len(changed) > limits.max_files:
        violations.append(
            Violation("diff-too-large", "*", f"{len(changed)} files changed (max {limits.max_files})")
        )
    if changed_lines > limits.max_changed_lines:
        violations.append(
            Violation(
                "diff-too-large", "*", f"{changed_lines} lines changed (max {limits.max_changed_lines})"
            )
        )
    return violations


def check_edit(rel_path: str, before: str, after: str, import_names: Iterable[str]) -> list[Violation]:
    """Early feedback for a single edit. The verifier still runs the full check at the end."""
    return [
        v
        for v in check_changes({rel_path: before}, {rel_path: after}, import_names, Limits(10**6, 10**6))
        if v.rule != "diff-too-large"
    ]


def count_tests(sources: dict[str, str]) -> int:
    return sum(_test_stats(text)[0] for p, text in sources.items() if is_test_file(p))


def _test_integrity(rel_path: str, before: str, after: str) -> list[Violation]:
    tests_before, asserts_before = _test_stats(before)
    tests_after, asserts_after = _test_stats(after)
    out = []
    if tests_after < tests_before:
        out.append(Violation("removes-tests", rel_path, f"test functions {tests_before} -> {tests_after}"))
    if asserts_after < asserts_before:
        out.append(Violation("weakens-tests", rel_path, f"assertions {asserts_before} -> {asserts_after}"))
    return out


def _test_stats(text: str) -> tuple[int, int]:
    """(test functions, assertions). ``pytest.raises`` and ``pytest.warns`` count as assertions."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return 0, 0
    tests = asserts = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test"):
            tests += 1
        elif isinstance(node, ast.Assert) or (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"raises", "warns"}
        ):
            asserts += 1
    return tests, asserts


def _changed_line_count(before: str, after: str) -> int:
    return sum(
        1
        for line in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    )
