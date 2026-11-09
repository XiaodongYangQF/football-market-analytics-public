#!/usr/bin/env python3
"""Verify that public repository text and documentation filenames remain English-only."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u3400-\u9fff]")
TEXT_EXTENSIONS = {".md", ".py", ".sh", ".txt", ".toml", ".yml", ".yaml", ".json", ".csv"}


def checked_files(root: Path = ROOT) -> list[Path]:
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                            cwd=root, check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        # A copied patch can be tested before Git initialization.
        return sorted(p for p in root.rglob("*") if p.is_file()
                      and not set(p.relative_to(root).parts) & {".git", "__pycache__", ".pytest_cache", ".venv", "venv"})
    names = (Path(x.decode("utf-8")) for x in result.stdout.split(b"\0") if x)
    return sorted({root / p for p in names if (root / p).is_file()})


def violations(root: Path = ROOT) -> list[str]:
    found = []
    for path in checked_files(root):
        rel = path.relative_to(root).as_posix()
        if rel.endswith("_CN.md") or CJK.search(rel):
            found.append(f"Non-English document filename: {rel}")
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            contents = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(contents.splitlines(), 1):
            if CJK.search(line):
                found.append(f"Chinese text in {rel}:{i}")
    return found


def main() -> int:
    errors = violations()
    if errors:
        print("PUBLIC ENGLISH CHECK FAILED:")
        for error in errors[:60]:
            print(f"  {error}")
        if len(errors) > 60:
            print(f"  ... plus {len(errors) - 60} more")
        return 1
    print("PUBLIC ENGLISH CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
