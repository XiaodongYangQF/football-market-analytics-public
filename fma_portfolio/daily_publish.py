"""Conservative release reconciliation for Local Public -> GitHub Portfolio.

The source is the *already published* Local Public tracker snapshot, never a
Private analysis ledger. This module never reconstructs the forecasting model.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from fma_portfolio.metrics import summarize
from fma_portfolio.release import validate_release
from fma_portfolio.settlement import verify_saved_record

MANIFEST_SCHEMA = "FMA_PUBLIC_RELEASE_MANIFEST_V1"


class ReleaseBlocked(ValueError):
    """A historical forecast would be silently lost or changed."""


def _match_key(row: Mapping[str, Any]) -> tuple:
    return tuple(row[k] for k in ("source_date", "competition", "fixture", "market"))


def _signal_fingerprint(row: Mapping[str, Any]) -> tuple:
    # Fields that must never be retroactively revised in the public ledger.
    return _match_key(row) + tuple(row[k] for k in ("direction", "line", "decimal_odds", "stake_u"))


def _is_signal(row: Mapping[str, Any]) -> bool:
    return row["direction"] != "NO SIGNAL"


def validate_settlements(release: Mapping[str, Any]) -> None:
    validate_release(dict(release))
    ids = [r["record"] for r in release["records"]]
    if len(ids) != len(set(ids)):
        raise ReleaseBlocked("Duplicate public record identifiers")
    for r in release["records"]:
        state = r["state"]
        if state == "SETTLED":
            if (r["line"] is None or r["decimal_odds"] is None or
                    r["stake_u"] is None or not r["final_score"]):
                raise ReleaseBlocked(f"Incomplete settlement fields: {r['record']}")
            try:
                ok = verify_saved_record(r)
            except (ValueError, TypeError, KeyError) as exc:
                raise ReleaseBlocked(f"Unverifiable settlement for {r['record']}: {exc}") from exc
            if not ok:
                raise ReleaseBlocked(f"Settlement/P&L arithmetic does not match: {r['record']}")
        elif r["pnl_u"] is not None or r["settlement"] is not None:
            raise ReleaseBlocked(f"Unsettled record includes profit or settlement: {r['record']}")


@dataclass(frozen=True)
class ReleaseDiff:
    old_rows: int
    new_rows: int
    old_settled: int
    new_settled: int
    placeholder_replacements: tuple[tuple, ...]
    new_signal_count: int
    new_settlement_count: int
    changed: bool


def audit_transition(old: Mapping[str, Any], new: Mapping[str, Any]) -> ReleaseDiff:
    """No silent deletion or rewriting of published predictions or settled results.

    An old NO SIGNAL/NOT_RECORDED placeholder may be replaced by a real
    record *for the same fixture and market*; this transition is reported.
    Genuine forecasts are immutable. An existing pending result may settle.
    A previously settled result can only be corrected by a separately reviewed
    workflow, never silently via this daily publisher.
    """
    validate_settlements(old)
    validate_settlements(new)
    past, future = old["records"], new["records"]
    older_signals = Counter(_signal_fingerprint(r) for r in past if _is_signal(r))
    later_signals = Counter(_signal_fingerprint(r) for r in future if _is_signal(r))
    missing = older_signals - later_signals
    if missing:
        raise ReleaseBlocked(f"Previously published signal disappeared/changed: {list(missing.items())[:3]}")

    later_by_match: dict[tuple, list] = defaultdict(list)
    later_by_record = {r["record"]: r for r in future}
    for r in future:
        later_by_match[_match_key(r)].append(r)

    replaced = []
    for r in past:
        if _is_signal(r):
            # Record IDs are deterministic from quote inputs, but even if the ID
            # algorithm changes, the immutable market/side/line/price still wins.
            if r["state"] == "SETTLED":
                counterpart = next((n for n in future
                                    if _signal_fingerprint(n) == _signal_fingerprint(r)
                                    and n["state"] == "SETTLED"
                                    and n["final_score"] == r["final_score"]
                                    and n["settlement"] == r["settlement"]
                                    and n["pnl_u"] == r["pnl_u"]), None)
                if counterpart is None:
                    raise ReleaseBlocked(f"Previously settled result changed: {r['record']}")
        else:
            candidates = later_by_match.get(_match_key(r), [])
            if not candidates:
                raise ReleaseBlocked(f"NO SIGNAL placeholder disappeared without replacement: {r['record']}")
            if not any(n["direction"] == "NO SIGNAL" for n in candidates):
                replaced.append(_match_key(r))

    new_signal_count = sum((later_signals - older_signals).values())
    old_settled_keys = Counter(_signal_fingerprint(r) for r in past if r["state"] == "SETTLED")
    new_settled_keys = Counter(_signal_fingerprint(r) for r in future if r["state"] == "SETTLED")
    new_settlement_count = sum((new_settled_keys - old_settled_keys).values())
    return ReleaseDiff(
        old_rows=len(past), new_rows=len(future),
        old_settled=sum(r["state"] == "SETTLED" for r in past),
        new_settled=sum(r["state"] == "SETTLED" for r in future),
        placeholder_replacements=tuple(replaced),
        new_signal_count=new_signal_count,
        new_settlement_count=new_settlement_count,
        changed=past != future,
    )


def make_manifest(release: Mapping[str, Any], source_sha256: str,
                  released_at_utc: str | None = None) -> dict[str, Any]:
    counts = Counter(r["state"] for r in release["records"])
    stats = summarize(release["records"])
    return {
        "schema": MANIFEST_SCHEMA,
        "released_at_utc": released_at_utc or datetime.now(timezone.utc).isoformat(),
        "source_public_snapshot_sha256": source_sha256,
        "records_sha256": hashlib.sha256(json.dumps(release["records"],
            ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "row_count": len(release["records"]),
        "settled_signals": stats["settled_signals"],
        "no_signal_rows": counts["NO_SIGNAL"],
        "not_recorded_rows": counts["NOT_RECORDED"],
        "pending_rows": sum(n for s, n in counts.items()
                            if s not in ("SETTLED", "NO_SIGNAL", "NOT_RECORDED")),
        "turnover_u": stats["turnover_u"],
        "pnl_u": stats["pnl_u"],
        "roi_pct": stats["roi_pct"],
        "note": "Manual public snapshot release; does not prove pre-kickoff publication or real trades.",
    }
