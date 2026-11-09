#!/usr/bin/env python3
"""P8.2F: Local Public allowlisted feed -> existing GitHub Issue publisher.

Default is DRY RUN. This script deliberately cannot open Private cases/ledgers or
execute/reconstruct scientific forecasts. The local-only exporter, installed
in the *other* project, must prepare a vetted P7.4-shaped feed first.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fma_portfolio.p7.saved_forecasts import parse_archive, SavedForecastsError
from fma_portfolio.prematch_receipts import utc, ReceiptError


class BridgeBlocked(ValueError):
    pass


def validate_feed_path(path: Path) -> Path:
    if not path.is_file() or path.is_symlink() or path.parent.is_symlink():
        raise BridgeBlocked("Expected a real Local Public receipt export file (not a symlink)")
    resolved = path.expanduser().resolve(strict=True)
    if ROOT.resolve() == resolved or ROOT.resolve() in resolved.parents:
        raise BridgeBlocked("Source feed must remain outside the public GitHub repository")
    parts = resolved.parts
    if (len(parts) < 5 or parts[-2] != "receipt_exports" or parts[-3] != "public_data" or
            parts[-4] != "football_market_analytics_v2_2"):
        raise BridgeBlocked("Only the Local Public public_data/receipt_exports/ feed is accepted")
    return resolved


def prepare_command(source: Path, *, kickoff: str, fixture_date: str, competition: str,
                    kickoff_basis: str, quote_source: str, publish: bool) -> list[str]:
    records = parse_archive(source.read_bytes())
    if not records or len(records) > 20:
        raise BridgeBlocked("Receipt feed must contain 1–20 records")
    if any(r["fixture_date"] != fixture_date or r["competition"] != competition for r in records):
        raise BridgeBlocked("Receipt feed includes fixtures outside the selected date/competition")
    when = utc(kickoff)
    try:
        day = date.fromisoformat(fixture_date)
    except ValueError as exc:
        raise BridgeBlocked("Invalid selected fixture date") from exc
    if abs((when.date() - day).days) > 1:
        raise BridgeBlocked("Kickoff does not agree with selected fixture date")
    command = [sys.executable, str(ROOT / "scripts" / "publish_prematch_receipt.py"),
               "--archive", str(source), "--fixture-date", fixture_date,
               "--competition", competition, "--kickoff-utc", kickoff,
               "--kickoff-basis", kickoff_basis, "--quote-source", quote_source]
    if publish:
        command.append("--publish")
    return command


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--feed", type=Path, required=True, help="Prepared allowlisted Local Public JSON only")
    p.add_argument("--fixture-date", required=True)
    p.add_argument("--competition", required=True)
    p.add_argument("--kickoff-utc", required=True, help="Official kickoff in ISO UTC; manually confirmed")
    p.add_argument("--kickoff-basis", required=True, help="Public official kickoff schedule source")
    p.add_argument("--quote-source", required=True, help="Truthful quote source and time verification status")
    p.add_argument("--publish", action="store_true", help="Explicitly allow GitHub Issue publication")
    args = p.parse_args(argv)
    try:
        src = validate_feed_path(args.feed)
        cmd = prepare_command(src, kickoff=args.kickoff_utc, fixture_date=args.fixture_date,
                              competition=args.competition, kickoff_basis=args.kickoff_basis,
                              quote_source=args.quote_source, publish=args.publish)
        print("P8.2F: GitHub receives only the already-curated Local Public feed; never Private files.", flush=True)
        result = subprocess.run(cmd, cwd=ROOT, check=False)
        return result.returncode
    except (BridgeBlocked, ReceiptError, SavedForecastsError, OSError, ValueError) as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
