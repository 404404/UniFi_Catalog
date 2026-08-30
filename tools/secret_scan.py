#!/usr/bin/env python3
"""Fail-closed secret scanner for catalog-controlled files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)authorization\s*[:=]"),
    re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|session[_-]?cookie|password)\s*[:=]"),
    re.compile(r"(?i)\b(?:ssh_password|controller_token|private_key)\b"),
    re.compile(r"(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b"),
)


class SecretScanError(RuntimeError):
    """Raised when scanning cannot complete or a secret-like value is found."""


def _files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        path = Path(path)
        if not path.exists():
            raise SecretScanError(f"scan target does not exist: {path}")
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(item for item in path.rglob("*") if item.is_file())
        else:
            raise SecretScanError(f"scan target is not a regular file or directory: {path}")
    return sorted(set(files))


def scan_paths(paths: Iterable[Path]) -> int:
    """Scan all readable files under paths and return the number inspected."""
    files = _files(paths)
    findings: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise SecretScanError(f"cannot read {path}: {exc}") from exc
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in PATTERNS:
                if pattern.search(line):
                    findings.append(f"{path}:{line_number}: {pattern.pattern}")
    if findings:
        raise SecretScanError("secret-like content found:\n" + "\n".join(findings))
    return len(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)
    try:
        scanned = scan_paths(args.paths)
    except Exception as exc:
        print(f"SECRET_SCAN=FAIL: {exc}")
        return 1
    print(f"SECRET_SCAN=PASS files={scanned}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
