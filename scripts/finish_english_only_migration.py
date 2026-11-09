#!/usr/bin/env python3
"""Remove known legacy language-specific docs after English replacements exist."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OLD_DOCUMENTS = (
    "INSTALL_CN.md",
    "P8_1B_HANDOFF_CN.md",
    "P8_1B_SCHEDULE_FIX_CN.md",
    "P8_1C2E_ELIGIBILITY_GATE_CN.md",
    "P8_1C2_EXTRACTION_DIAGNOSTIC_FIX_CN.md",
    "P8_1C2_MAC_TEST_HOTFIX_CN.md",
    "P8_1C2_RESUMABLE_MAC_BASELINE_CN.md",
    "P8_1C2_SCIENTIFIC_PARITY_CN.md",
    "P8_1C_HOSTED_PILOT_CN.md",
    "P8_1D_DAILY_PUBLISH_HANDOFF_CN.md",
    "P8_1E_PREMATCH_RECEIPTS_CN.md",
    "P8_2D_PUBLIC_LAUNCH_CN.md",
    "P8_2E_FIRST_RECEIPT_ACCEPTANCE_CN.md",
    "P8_2F_LOCAL_PUBLIC_RECEIPT_BRIDGE_CN.md",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Back up and remove the legacy documents")
    args = parser.parse_args()
    present = []
    for name in OLD_DOCUMENTS:
        english = ROOT / name.replace("_CN.md", ".md")
        if not english.is_file():
            raise SystemExit(f"STOPPED: Missing English replacement: {english}")
        old = ROOT / name
        if old.is_file():
            if old.is_symlink() or english.is_symlink():
                raise SystemExit(f"STOPPED: Refusing document symlink: {name}")
            present.append(old)
    if not present:
        print("OK: No legacy language-specific documents remain.")
        return 0
    print(f"Legacy documents to remove: {len(present)}")
    for old in present:
        print(f"  {old.name} -> {old.name.replace('_CN.md', '.md')}")
    if not args.apply:
        print("DRY RUN: No files removed. Add --apply after review.")
        return 0
    # Do not destroy local changes to a tracked legacy document.
    for old in present:
        result = subprocess.run(["git", "diff", "--quiet", "--", old.name], cwd=ROOT, check=False)
        if result.returncode == 1:
            raise SystemExit(f"STOPPED: Uncommitted edits in {old.name}; review before migration.")
        if result.returncode not in (0, 1):
            raise SystemExit(f"STOPPED: Git comparison failed for {old.name}")
    backup = Path.home() / "fma_patch_backups" / "p8_2g_english_migration"
    backup.mkdir(parents=True, exist_ok=True)
    for old in present:
        target = backup / old.name
        if target.exists():
            raise SystemExit(f"STOPPED: Backup already exists: {target}")
    for old in present:
        shutil.copy2(old, backup / old.name)
        old.unlink()
    print(f"DONE: Removed {len(present)} legacy docs; backups outside repo: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
