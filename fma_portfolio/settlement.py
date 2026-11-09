"""Independent Asian handicap / Asian total settlement arithmetic.

This is generic public mathematics. It does not derive or expose the
proprietary forecast rules. Decimal odds are the public recorded quotes.
"""
from __future__ import annotations

import math
import re
from typing import Mapping

SCORE_PATTERN = re.compile(r"^\s*(\d+)\s*[-–—:]\s*(\d+)\s*$")


def _half_lines(line: float) -> tuple[float, ...]:
    quarters = round(line * 4)
    if not math.isclose(quarters / 4, line, abs_tol=1e-7):
        raise ValueError("Line must be in quarter-goal increments")
    return (line - 0.25, line + 0.25) if quarters % 2 else (line,)


def _score_pair(score: str) -> tuple[int, int]:
    m = SCORE_PATTERN.fullmatch(score)
    if not m:
        raise ValueError("Expected a ninety-minute score such as 2–1")
    return int(m.group(1)), int(m.group(2))


def settle(market: str, direction: str, line: float, decimal_odds: float,
           score: str, stake_u: float = 1.0) -> tuple[str, float]:
    if stake_u <= 0 or decimal_odds <= 1:
        raise ValueError("Expected positive stake and decimal odds greater than one")
    home, away = _score_pair(score)
    if (market, direction) not in {("AH", "HOME"), ("AH", "AWAY"), ("OU", "OVER"), ("OU", "UNDER")}:
        raise ValueError("Unsupported market/direction")
    part_results = []
    for component in _half_lines(float(line)):
        if market == "AH":
            goal_margin = home - away if direction == "HOME" else away - home
            diff = goal_margin + component
        else:
            total_goals = home + away
            diff = total_goals - component if direction == "OVER" else component - total_goals
        part_results.append(1 if diff > 1e-8 else -1 if diff < -1e-8 else 0)
    if len(part_results) == 1:
        outcome = {1: "WIN", 0: "PUSH", -1: "LOSS"}[part_results[0]]
    else:
        labels = tuple(sorted(part_results))
        outcome = {(-1, -1): "LOSS", (-1, 0): "HALF_LOSS", (-1, 1): "MIXED",
                   (0, 0): "PUSH", (0, 1): "HALF_WIN", (1, 1): "WIN"}[labels]
    profit = sum((decimal_odds - 1) if p == 1 else (-1 if p == -1 else 0)
                 for p in part_results) / len(part_results) * stake_u
    return outcome, round(profit, 8)


def verify_saved_record(row: Mapping) -> bool:
    if row["state"] != "SETTLED":
        return True
    category, pnl = settle(row["market"], row["direction"], float(row["line"]),
                           float(row["decimal_odds"]), str(row["final_score"]),
                           float(row["stake_u"]))
    return category == row["settlement"] and math.isclose(pnl, float(row["pnl_u"]), abs_tol=1e-7)
