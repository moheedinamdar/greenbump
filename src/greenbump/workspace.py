"""A throwaway copy of the target repository that the agent is allowed to edit."""

from __future__ import annotations

import difflib
import os
import shutil
from pathlib import Path

IGNORED_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "node_modules",
    ".greenbump",
    ".greenbump-cache",
    "build",
    "dist",
    ".eggs",
    ".DS_Store",
}
MAX_TEXT_BYTES = 1_000_000


class WorkspaceError(ValueError):
    """A path or edit that the workspace refuses."""


class Workspace:
    def __init__(self, source: Path, root: Path) -> None:
        self.source = source.resolve()
        if not self.source.is_dir():
            raise WorkspaceError(f"repository {source} is not a directory")
        if root.exists():
            raise WorkspaceError(f"work directory {root} already exists")
        shutil.copytree(self.source, root, symlinks=True, ignore=_ignore)
        self.root = root.resolve()
        self.original = self.snapshot()

    def resolve(self, rel_path: str) -> Path:
        """Map a repo-relative path to a real path, refusing anything outside the work copy."""
        if not rel_path or os.path.isabs(rel_path):
            raise WorkspaceError(f"path must be relative to the repository root: {rel_path!r}")
        target = (self.root / rel_path).resolve()
        if not target.is_relative_to(self.root):
            raise WorkspaceError(f"path escapes the repository: {rel_path!r}")
        return target

    def rel(self, target: Path) -> str:
        return target.relative_to(self.root).as_posix()

    def python_files(self) -> list[str]:
        return sorted(p for p in self.snapshot() if p.endswith(".py"))

    def read(self, rel_path: str) -> str:
        target = self.resolve(rel_path)
        if not target.is_file():
            raise WorkspaceError(f"no such file: {rel_path}")
        return target.read_text(encoding="utf-8")

    def write(self, rel_path: str, text: str) -> None:
        target = self.resolve(rel_path)
        if not target.is_file():
            raise WorkspaceError(f"no such file: {rel_path} (greenbump only edits existing files)")
        target.write_text(text, encoding="utf-8")

    def replace(self, rel_path: str, old: str, new: str, replace_all: bool = False) -> int:
        text = self.read(rel_path)
        count = text.count(old) if old else 0
        if count == 0:
            raise WorkspaceError(
                f"old_text not found in {rel_path}. Copy it exactly from read_file, without line numbers."
            )
        if count > 1 and not replace_all:
            raise WorkspaceError(
                f"old_text appears {count} times in {rel_path}. Add surrounding lines or set replace_all."
            )
        self.write(rel_path, text.replace(old, new) if replace_all else text.replace(old, new, 1))
        return count if replace_all else 1

    def snapshot(self) -> dict[str, str]:
        """All UTF-8 text files in the work copy, keyed by repo-relative path."""
        files: dict[str, str] = {}
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_NAMES)
            for name in sorted(filenames):
                if name in IGNORED_NAMES or name.endswith(".pyc"):
                    continue
                full = Path(dirpath) / name
                if full.is_symlink() or full.stat().st_size > MAX_TEXT_BYTES:
                    continue
                try:
                    text = full.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                files[full.relative_to(self.root).as_posix()] = text
        return files

    def changed_files(self) -> list[str]:
        now = self.snapshot()
        return sorted(p for p in set(now) | set(self.original) if now.get(p) != self.original.get(p))

    def diff(self) -> str:
        now = self.snapshot()
        chunks: list[str] = []
        for rel_path in self.changed_files():
            chunks.extend(
                difflib.unified_diff(
                    self.original.get(rel_path, "").splitlines(keepends=True),
                    now.get(rel_path, "").splitlines(keepends=True),
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                )
            )
        return "".join(line if line.endswith("\n") else line + "\n" for line in chunks)

    def clear_bytecode(self) -> None:
        for cache in self.root.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


def _ignore(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n in IGNORED_NAMES or n.endswith(".pyc")}
