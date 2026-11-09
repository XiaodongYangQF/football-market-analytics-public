import copy
from pathlib import Path
import json

import pytest

from fma_portfolio.release import sanitize_snapshot, load_release, PUBLIC_RECORD_FIELDS, RELEASE_SCHEMA

ROOT = Path(__file__).resolve().parents[1]


def example_snapshot():
    return {
        "schema": "FMA_PUBLIC_TRACKER_V1", "generated_at": "2026-11-08T00:00:00Z",
        "rows": [
            {"policy_basis": "POST_ACTIVATION_V2", "date": "2026-11-08", "league": "La Liga",
             "match": "Example vs Fixture", "market": "AH", "prediction": "HOME", "line": -0.5,
             "odds": 1.95, "weight_u": 1.0, "score": "2–0", "state": "SETTLED",
             "settlement": "WIN", "pnl_u": 0.95, "pricing_evidence": "FROZEN_EXECUTION",
             "analysis_id": "PRIVATE_INTERNAL_123", "trade_id": "PRIVATE_TRADE_123",
             "secret_extra": "SHOULD_NOT_APPEAR", "rule_id": "AH-V1-A"},
            {"policy_basis": "RETROSPECTIVE_REWEIGHTED", "date": "2026-09-10", "league": "La Liga",
             "match": "Old vs Old", "market": "OU", "prediction": "OVER", "state": "NO_SIGNAL"},
        ],
    }


def test_allowlisted_release_is_deterministic_and_does_not_mutate_input():
    source = example_snapshot()
    original = copy.deepcopy(source)
    out1, out2 = sanitize_snapshot(source), sanitize_snapshot(source)
    assert out1 == out2
    assert source == original
    assert out1["schema"] == RELEASE_SCHEMA
    assert len(out1["records"]) == 1
    assert set(out1["records"][0]) == PUBLIC_RECORD_FIELDS
    assert "PRIVATE_INTERNAL_123" not in json.dumps(out1)
    assert "PRIVATE_TRADE_123" not in json.dumps(out1)
    assert "AH-V1-A" not in json.dumps(out1)
    assert "secret_extra" not in json.dumps(out1)


def test_no_private_ledger_is_accepted():
    with pytest.raises(ValueError):
        sanitize_snapshot({"schema": "PRIVATE_2026", "rows": []})


def test_reject_inconsistent_settlement():
    source = example_snapshot()
    source["rows"][0]["pnl_u"] = None
    with pytest.raises(ValueError):
        sanitize_snapshot(source)


def test_curated_release_structure():
    data = load_release(ROOT / "data/public_v2.json")
    assert data["cohort"].startswith("Public V2")
    assert all(r["record"].startswith("V2-") for r in data["records"])
    assert all(set(r) == PUBLIC_RECORD_FIELDS for r in data["records"])


def test_no_direct_private_imports_in_public_app():
    text = (ROOT / "app.py").read_text()
    for item in ("from backend", "import backend", "from core", "runtime_data", "analysis_snapshot"):
        assert item not in text
