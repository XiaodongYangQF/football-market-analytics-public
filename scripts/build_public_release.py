#!/usr/bin/env python3
"""Create an explicitly allowlisted, PUBLIC-only release for this repository."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fma_portfolio.metrics import summarize
from fma_portfolio.release import sanitize_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe Local Public -> Portfolio export (read-only)")
    parser.add_argument("--snapshot", type=Path, required=True, help="Local Public tracker_snapshot.json")
    parser.add_argument("--output", type=Path, default=Path("data/public_v2.json"))
    args = parser.parse_args()
    if not args.snapshot.is_file():
        parser.error("Snapshot file not found")
    source = json.loads(args.snapshot.read_text(encoding="utf-8"))
    release = sanitize_snapshot(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(release, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = summarize(release["records"])
    print(f"Safe public release: {len(release['records'])} records, "
          f"{summary['settled_signals']} settled, {summary['pnl_u']:+.4f}u, "
          f"ROI {summary['roi_pct']:.2f}%")
    print(f"Written: {args.output.resolve()}")

if __name__ == "__main__":
    main()
