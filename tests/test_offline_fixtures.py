"""Offline P8 public fixture data integrity and API removal regression checks."""
from pathlib import Path

from fma_portfolio.p7.fixtures_store import load_fixtures, fixture_options
from fma_portfolio.p7.forecast_ui import manual_team_choices

ROOT = Path(__file__).resolve().parents[1]
LEAGUES = ("E0", "D1", "SP1", "I1", "F1")


def test_public_fixtures_five_leagues_and_canonical_names():
    path = ROOT / "data/fixtures.csv"
    for code in LEAGUES:
        items = load_fixtures(path, code)
        assert items, f"Missing fixtures for {code}"
        assert all(item["canonical_home"] and item["canonical_away"] for item in items)


def test_offline_picker_has_upcoming_fixtures_in_reference_snapshot():
    path = ROOT / "data/fixtures.csv"
    items = load_fixtures(path, "E0")
    assert fixture_options(items, "Upcoming", __import__("datetime").date(2026, 11, 18))


def test_manual_team_roster_remains_available():
    assert ("Aston Villa", "Aston Villa") in manual_team_choices("E0")
    assert ("Sunderland", "Sunderland") in manual_team_choices("E0")


def test_forecast_ui_does_not_depend_on_hosted_fixture_api():
    source = (ROOT / "fma_portfolio/p7/forecast_ui.py").read_text(encoding="utf-8")
    assert "cloud_fixtures" not in source
    assert "fetch_api_schedule" not in source
    assert "FMA_FIXTURE_API_TOKEN" not in source
