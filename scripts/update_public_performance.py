#!/usr/bin/env python3
"""Read-only preview by default; explicit --apply updates only two public files."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fma_portfolio.release import load_release, sanitize_snapshot
from fma_portfolio.metrics import summarize
from fma_portfolio.daily_publish import audit_transition, make_manifest, validate_settlements, ReleaseBlocked

DEFAULT_SOURCE = ROOT.parent / "football_market_analytics_v2_2" / "public_data" / "tracker_snapshot.json"
TARGET = ROOT / "data" / "public_v2.json"
MANIFEST = ROOT / "data" / "public_release_manifest.json"


def _atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    fd, name = tempfile.mkstemp(prefix=".fma-public-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(serialized)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Local Public -> GitHub Public: daily performance snapshot")
    p.add_argument("--snapshot", type=Path, default=DEFAULT_SOURCE, help="Read-only Local Public snapshot")
    p.add_argument("--apply", action="store_true", help="Write only curated Public release + manifest")
    args = p.parse_args(argv)
    source = args.snapshot.expanduser().resolve()
    # Never use a Private ledger or a file placed inside the public repo.
    if ROOT.resolve() in source.parents:
        p.error("Source snapshot must be outside the public repository")
    if source.name != "tracker_snapshot.json" or not source.is_file():
        p.error("Expected an existing Local Public tracker_snapshot.json")

    try:
        data_bytes = source.read_bytes()
        source_obj = json.loads(data_bytes)
        candidate = sanitize_snapshot(source_obj)
        validate_settlements(candidate)
        current = load_release(TARGET)
        diff = audit_transition(current, candidate)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
        print(f"STOPPED: {e}", file=sys.stderr)
        return 2

    old = summarize(current["records"])
    new = summarize(candidate["records"])
    print("== LOCAL PUBLIC → GITHUB PUBLIC · PREVIEW ==")
    old_roi = f"{old['roi_pct']:.2f}%" if old['roi_pct'] is not None else 'n/a'
    new_roi = f"{new['roi_pct']:.2f}%" if new['roi_pct'] is not None else 'n/a'
    print(f"Existing: {diff.old_rows} rows / {diff.old_settled} settled / {old['pnl_u']:+.4f}u / {old_roi} ROI")
    print(f"Candidate: {diff.new_rows} rows / {diff.new_settled} settled / {new['pnl_u']:+.4f}u / {new_roi} ROI")
    print(f"New signals: {diff.new_signal_count}; newly settled: {diff.new_settlement_count}; "
          f"NO SIGNAL replacements: {len(diff.placeholder_replacements)}")
    if diff.placeholder_replacements:
        for k in diff.placeholder_replacements[:15]:
            print("  PLACEHOLDER REPLACEMENT:", " | ".join(map(str, k)))
    manifest_missing = not MANIFEST.is_file()
    if not diff.changed and not manifest_missing:
        print("NO DATA CHANGE: existing release is current. Nothing written.")
        return 0
    if not diff.changed and manifest_missing:
        print("Public records unchanged; initial release manifest has not yet been created.")
    if not args.apply:
        print("DRY RUN PASS: no files changed. Re-run with --apply to update public data.")
        return 0

    digest = hashlib.sha256(data_bytes).hexdigest()
    manifest = make_manifest(candidate, digest)
    if diff.changed:
        _atomic_json(TARGET, candidate)
    _atomic_json(MANIFEST, manifest)
    print("APPLIED: " +
          ("data/public_v2.json + " if diff.changed else "") +
          "data/public_release_manifest.json")
    print("NOT pushed to GitHub. Run security check, unit tests, review git diff, then push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
