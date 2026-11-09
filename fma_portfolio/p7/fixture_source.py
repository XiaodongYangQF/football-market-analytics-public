"""Resolve the optional owner-local P7 Public schedule without packaging it.

Never use the owner project in hosted mode. In owner-local loopback mode,
read the pre-existing Public Web Edition's fixture CSV; do not copy it to Git.
"""
from __future__ import annotations

from pathlib import Path


def fixture_source(published_path: Path, *, owner_local: bool,
                   project_root: str | None = None) -> tuple[Path, bool]:
    """Return (fixture_csv_path, using_owner_local_public_schedule)."""
    if owner_local and project_root and project_root.strip():
        candidate = (Path(project_root).expanduser() / 'deployment' / 'public_web'
                     / 'data' / 'fixtures.csv')
        if candidate.is_file():
            return candidate, True
    return published_path, False
