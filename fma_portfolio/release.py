"""Allowlisted transformation from the read-only Local Public snapshot.

DO NOT consume the Private runtime database, internal rule engine, or strategy
code.  Only a known public snapshot with the published V2 cohort is accepted.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

SOURCE_SCHEMA = "FMA_PUBLIC_TRACKER_V1"
RELEASE_SCHEMA = "FMA_PORTFOLIO_PUBLIC_V1"
V2_BASIS = "POST_ACTIVATION_V2"
_ALLOWED_MARKETS = {"AH", "OU"}
_ALLOWED_STATES = {"SETTLED", "NO_SIGNAL", "NOT_RECORDED", "AWAITING_RESULT", "REPLAY_UNAVAILABLE"}
PUBLIC_RECORD_FIELDS = frozenset({
    "record", "source_date", "competition", "fixture", "market", "direction",
    "line", "decimal_odds", "stake_u", "final_score", "state",
    "settlement", "pnl_u", "price_evidence",
})
PUBLIC_TOP_FIELDS = frozenset({"schema", "cohort", "source_snapshot_generated_at_utc", "description", "records"})


def _optional_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Unexpected numeric input type: {type(value).__name__}")
    return float(value)


def sanitize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    if snapshot.get("schema") != SOURCE_SCHEMA or not isinstance(snapshot.get("rows"), list):
        raise ValueError("Expected a Local Public tracker snapshot, not a Private data file")
    records = []
    for raw in snapshot["rows"]:
        if raw.get("policy_basis") != V2_BASIS:
            continue
        market = raw.get("market")
        state = raw.get("state")
        direction = raw.get("prediction")
        if market not in _ALLOWED_MARKETS or state not in _ALLOWED_STATES:
            raise ValueError("Unsupported Public V2 market or state")
        if direction not in {"HOME", "AWAY", "OVER", "UNDER", "NO SIGNAL"}:
            raise ValueError("Unsupported Public V2 direction")
        if (state == "SETTLED") != (raw.get("pnl_u") is not None):
            raise ValueError("Inconsistent settled-state P&L fields")
        if state == "SETTLED" and (raw.get("weight_u") is None or raw.get("odds") is None):
            raise ValueError("Settled record missing stake or odds")
        # Construct every field manually. Never copy or expose an internal id,
        # rule name, policy identifier, analysis id, path, or provenance payload.
        records.append({
            "record": "",  # assigned after a deterministic public sort
            "source_date": str(raw["date"]),
            "competition": str(raw["league"]),
            "fixture": str(raw["match"]),
            "market": market,
            "direction": direction,
            "line": _optional_number(raw.get("line")),
            "decimal_odds": _optional_number(raw.get("odds")),
            "stake_u": _optional_number(raw.get("weight_u")),
            "final_score": raw.get("score"),
            "state": state,
            "settlement": raw.get("settlement"),
            "pnl_u": _optional_number(raw.get("pnl_u")),
            "price_evidence": str(raw.get("pricing_evidence") or "UNSPECIFIED"),
        })
    records.sort(key=lambda row: (
        row["source_date"], row["competition"], row["fixture"], row["market"],
        str(row["line"]), row["direction"], str(row["decimal_odds"]),
    ))
    seen_public_keys: dict[str, int] = {}
    for record in records:
        # Stable across later appended fixtures; no Private IDs used.
        key = "|".join(str(record[field]) for field in (
            "source_date", "competition", "fixture", "market", "direction", "line", "decimal_odds"
        ))
        occurrence = seen_public_keys.get(key, 0) + 1
        seen_public_keys[key] = occurrence
        digest = hashlib.sha256(f"{key}|{occurrence}".encode("utf-8")).hexdigest()[:12]
        record["record"] = f"V2-{digest}"
    result = {
        "schema": RELEASE_SCHEMA,
        "cohort": "Public V2 post-activation; historical snapshot",
        "source_snapshot_generated_at_utc": snapshot.get("generated_at"),
        "description": "Read-only, curated Public V2 outcomes; no private model code or data.",
        "records": records,
    }
    validate_release(result)
    return result


def validate_release(release: dict[str, Any]) -> None:
    if set(release) != PUBLIC_TOP_FIELDS or release["schema"] != RELEASE_SCHEMA:
        raise ValueError("Unexpected top-level release fields")
    if not isinstance(release["records"], list):
        raise ValueError("Records must be a list")
    for record in release["records"]:
        if set(record) != PUBLIC_RECORD_FIELDS:
            raise ValueError("Unexpected public record fields; possible data leak")
        if record["market"] not in _ALLOWED_MARKETS or record["state"] not in _ALLOWED_STATES:
            raise ValueError("Unexpected market/state")
        if record["state"] == "SETTLED" and record["pnl_u"] is None:
            raise ValueError("Settled row missing P&L")


def load_release(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    validate_release(result)
    return result
