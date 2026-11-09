"""Current release invariants + a separately retained initial-release regression sample."""
from pathlib import Path
import math

from fma_portfolio.metrics import summarize, group_summary, cumulative_by_source_date, outcome_counts
from fma_portfolio.release import load_release
from fma_portfolio.settlement import verify_saved_record

ROOT = Path(__file__).resolve().parents[1]
ROWS = load_release(ROOT / "data/public_v2.json")["records"]
INITIAL = load_release(ROOT / "tests/fixtures/initial_public_v2.json")["records"]


def test_public_data_states_and_trade_counts_are_consistent():
    assert ROWS
    assert len({r["record"] for r in ROWS}) == len(ROWS)
    assert sum(r["state"] == "SETTLED" for r in ROWS) == summarize(ROWS)["settled_signals"]


def test_initial_release_reference_is_unchanged():
    m = summarize(INITIAL)
    assert len(INITIAL) == 67
    assert sum(r["state"] == "SETTLED" for r in INITIAL) == 34
    assert math.isclose(m["turnover_u"], 34.0)
    assert math.isclose(m["pnl_u"], 3.8, abs_tol=1e-8)
    assert math.isclose(m["roi_pct"], 11.176470588, rel_tol=1e-8)


def test_current_release_aggregation_reconciles():
    s = summarize(ROWS)
    by_market = group_summary(ROWS, "market")
    assert sum(r["settled_signals"] for r in by_market) == s["settled_signals"]
    assert math.isclose(sum(r["pnl_u"] for r in by_market), s["pnl_u"], abs_tol=1e-8)
    assert math.isclose(sum(r["turnover_u"] for r in by_market), s["turnover_u"], abs_tol=1e-8)


def test_current_settlements_recompute_exactly():
    assert all(verify_saved_record(row) for row in ROWS)
    assert sum(outcome_counts(ROWS).values()) == summarize(ROWS)["settled_signals"]


def test_current_daily_series_adds_to_full():
    series = cumulative_by_source_date(ROWS)
    if series:
        assert math.isclose(series[-1]["cumulative_pnl_u"], summarize(ROWS)["pnl_u"], abs_tol=1e-8)


def test_no_signal_and_nonsettled_have_no_simulated_stake():
    assert all(r["stake_u"] is None and r["pnl_u"] is None
               for r in ROWS if r["state"] != "SETTLED")


def test_eur_unit_scaling_is_generic():
    s = summarize(ROWS)
    assert math.isclose(s["pnl_u"] * 20, sum(float(r["pnl_u"]) * 20 for r in ROWS
                                              if r["state"] == "SETTLED"), abs_tol=1e-7)
