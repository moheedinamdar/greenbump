"""Plain data types shared across modules."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Distribution names whose import name differs from the normalised distribution name.
KNOWN_IMPORT_NAMES = {
    "pyyaml": "yaml",
    "scikit-learn": "sklearn",
    "pillow": "PIL",
    "beautifulsoup4": "bs4",
    "python-dateutil": "dateutil",
    "opencv-python": "cv2",
    "attrs": "attr",
    "pyjwt": "jwt",
    "protobuf": "google.protobuf",
}


@dataclass(frozen=True)
class Bump:
    """One dependency that was upgraded."""

    package: str
    to_version: str
    from_version: str | None = None

    @property
    def import_name(self) -> str:
        key = self.package.lower()
        return KNOWN_IMPORT_NAMES.get(key, re.sub(r"[-.]+", "_", key))

    def describe(self) -> str:
        return f"{self.package} {self.from_version or '(old version)'} -> {self.to_version}"

    @classmethod
    def parse(cls, spec: str) -> Bump:
        """Parse ``name:to`` or ``name:from:to``."""
        parts = [p.strip() for p in spec.split(":")]
        if len(parts) == 2 and all(parts):
            return cls(package=parts[0], to_version=parts[1])
        if len(parts) == 3 and all(parts):
            return cls(package=parts[0], from_version=parts[1], to_version=parts[2])
        raise ValueError(f"bad --bump {spec!r}: use NAME:TO or NAME:FROM:TO, e.g. pydantic:1.10.27:2.14.3")


@dataclass
class TestRun:
    """The outcome of one pytest run."""

    returncode: int
    passed: int
    failed: int
    errors: int
    skipped: int
    xfailed: int
    output: str
    seconds: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out and not self.failed and not self.errors

    def headline(self) -> str:
        if self.timed_out:
            return "timed out"
        parts = [f"{self.passed} passed", f"{self.failed} failed", f"{self.errors} errors"]
        if self.skipped:
            parts.append(f"{self.skipped} skipped")
        if self.xfailed:
            parts.append(f"{self.xfailed} xfailed")
        return ", ".join(parts)
