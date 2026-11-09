"""Pure-Python performance summaries for a curated public forecast dataset.

All returns are simulated in units. A settled 1u stake can be scaled to any
currency amount; the analysis never asserts that a bet was actually placed.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping

SETTLED = "SETTLED"


def settled_rows(rows: Iterable[Mapping]) -> list[dict]:
    return [dict(row) for row in rows if row.get("state") == SETTLED]


def summarize(rows: Iterable[Mapping]) -> dict:
    selected = settled_rows(rows)
    stake = sum(float(row["stake_u"]) for row in selected)
    pnl = sum(float(row["pnl_u"]) for row in selected)
    return {
        "settled_signals": len(selected),
        "fixture_count": len({(r["source_date"], r["competition"], r["fixture"]) for r in selected}),
        "turnover_u": round(stake, 8),
        "pnl_u": round(pnl, 8),
        "roi_pct": 100 * pnl / stake if stake else None,
    }


def group_summary(rows: Iterable[Mapping], key: str) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or "Unknown")].append(row)
    return [{key: name, **summarize(group)} for name, group in sorted(groups.items())]


def cumulative_by_source_date(rows: Iterable[Mapping]) -> list[dict]:
    daily = group_summary(rows, "source_date")
    cumulative = 0.0
    result = []
    for entry in sorted(daily, key=lambda x: x["source_date"]):
        cumulative += entry["pnl_u"]
        result.append({"source_date": entry["source_date"],
                       "daily_pnl_u": entry["pnl_u"],
                       "cumulative_pnl_u": round(cumulative, 8),
                       "settled_signals": entry["settled_signals"]})
    return result


def outcome_counts(rows: Iterable[Mapping]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in settled_rows(rows):
        name = str(row.get("settlement") or "UNKNOWN")
        out[name] = out.get(name, 0) + 1
    return dict(sorted(out.items()))
