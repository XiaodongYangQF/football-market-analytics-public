"""No network test coverage for the P8 hosted fixture provider mapping."""
import json
from io import BytesIO
from urllib.error import HTTPError

from fma_portfolio.p7.cloud_fixtures import (
    parse_api_schedule, fetch_api_schedule, FixtureFeedUnavailable, manual_team_choices
)


def _sample():
    return {"matches": [
        {"status": "SCHEDULED", "utcDate": "2026-11-21T15:00:00Z",
         "homeTeam": {"shortName": "Aston Villa", "name": "Aston Villa FC"},
         "awayTeam": {"shortName": "Sunderland", "name": "Sunderland AFC"}},
        {"status": "FINISHED", "utcDate": "2026-11-10T15:00:00Z",
         "homeTeam": {"shortName": "Arsenal"}, "awayTeam": {"shortName": "Chelsea"}},
    ]}


def test_schedule_is_canonical_and_excludes_finished():
    rows = parse_api_schedule("E0", _sample())
    assert len(rows) == 1
    assert rows[0] == {"league": "E0", "fixture_date": "2026-11-21",
                       "home": "Aston Villa", "away": "Sunderland",
                       "canonical_home": "Aston Villa", "canonical_away": "Sunderland"}


def test_unknown_club_is_not_guessed():
    payload = _sample()
    payload["matches"][0]["homeTeam"]["shortName"] = "An invented club"
    payload["matches"][0]["homeTeam"]["name"] = "An invented club"
    assert parse_api_schedule("E0", payload) == []


def test_manual_choices_use_only_public_roster():
    choices = manual_team_choices("E0")
    assert ("Aston Villa", "Aston Villa") in choices
    assert ("Sunderland", "Sunderland") in choices


def test_http_contract_token_only_in_header():
    seen = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self, _): return json.dumps(_sample()).encode()
    def fetcher(req, timeout):
        seen["url"] = req.full_url
        seen["headers"] = dict(req.header_items())
        assert timeout == 12
        return Response()
    assert len(fetch_api_schedule("E0", api_token="valid_secret_token_12345", fetcher=fetcher)) == 1
    assert "valid_secret_token_12345" not in seen["url"]
    assert "valid_secret_token_12345" in seen["headers"].values()
