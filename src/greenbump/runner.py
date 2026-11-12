"""Run the target repository's test suite in a child process with a scrubbed environment.

This is process isolation, not a sandbox: the code under test runs as the current user.
Run greenbump inside a container or a throwaway VM when the repository is not yours.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

from .models import TestRun

_COUNT_RE = re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed)\b")
_TIMING_RE = re.compile(r"\bin \d+(?:\.\d+)?s\b")


def scrubbed_env(workdir: Path, python: str) -> dict[str, str]:
    """A minimal environment: no tokens, no proxies, no inherited PYTHONPATH."""
    import_roots = [workdir / "src", workdir] if (workdir / "src").is_dir() else [workdir]
    return {
        "PATH": os.pathsep.join([str(Path(python).parent), "/usr/bin", "/bin"]),
        "HOME": str(workdir),
        "LANG": "C.UTF-8",
        "PYTHONPATH": os.pathsep.join(str(p) for p in import_roots),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "NO_COLOR": "1",
    }


def run_pytest(workdir: Path, python: str, timeout: float = 180.0) -> TestRun:
    # abspath, not resolve(): a relative path would be looked up from cwd=workdir, and resolving
    # the venv symlink would lose the venv's site-packages.
    python = os.path.abspath(python)
    cmd = [python, "-m", "pytest", "-q", "--tb=short", "-rfE", "-p", "no:cacheprovider", "--color=no"]
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=workdir,
            env=scrubbed_env(workdir, python),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        out = redact_paths(_text(exc.stdout) + _text(exc.stderr), workdir, python)
        return TestRun(
            -1,
            0,
            0,
            0,
            0,
            0,
            out + f"\n[greenbump] pytest timed out after {timeout:.0f}s",
            time.monotonic() - start,
            timed_out=True,
        )
    except OSError as exc:
        return TestRun(
            -1, 0, 0, 1, 0, 0, f"[greenbump] could not start {python}: {exc}", time.monotonic() - start
        )
    output = redact_paths(proc.stdout + proc.stderr, workdir, python)
    counts = parse_summary(output)
    return TestRun(
        returncode=proc.returncode,
        passed=counts.get("passed", 0),
        failed=counts.get("failed", 0),
        errors=counts.get("errors", 0),
        skipped=counts.get("skipped", 0),
        xfailed=counts.get("xfailed", 0),
        output=output,
        seconds=time.monotonic() - start,
    )


def redact_paths(text: str, workdir: Path, python: str) -> str:
    """Replace machine-specific paths so prompts, logs and committed eval results stay portable."""
    venv = os.path.dirname(os.path.dirname(python))
    labels = [
        (str(workdir), "<repo>"),
        (os.path.realpath(workdir), "<repo>"),
        (venv, "<venv>"),
        (os.path.realpath(venv), "<venv>"),
        (sys.base_prefix, "<python>"),
        (os.path.realpath(sys.base_prefix), "<python>"),
        (str(Path.home()), "~"),
    ]
    for prefix, label in sorted(labels, key=lambda pair: len(pair[0]), reverse=True):
        if len(prefix) > 1:
            text = text.replace(prefix, label)
    return text


def parse_summary(output: str) -> dict[str, int]:
    """Read the counts from pytest's final summary line, e.g. ``2 failed, 5 passed in 0.12s``."""
    for line in reversed(output.splitlines()):
        if not _TIMING_RE.search(line):
            continue
        found = _COUNT_RE.findall(line)
        if not found and "no tests ran" not in line:
            continue
        counts: dict[str, int] = {}
        for number, word in found:
            key = "errors" if word.startswith("error") else word
            counts[key] = counts.get(key, 0) + int(number)
        return counts
    return {}


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value
