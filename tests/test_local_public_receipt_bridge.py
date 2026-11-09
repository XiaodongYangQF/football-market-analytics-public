"""P8.2F tests for public-only bridge, with NO Private installation required."""
from __future__ import annotations
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from publish_local_public_receipt import BridgeBlocked, validate_feed_path, prepare_command
from fma_portfolio.p7.saved_forecasts import archive_json


def sample():
    return {
        "record_id":"440e4a04-04a6-48f1-85af-ace75d7bc321",
        "saved_at_utc":"2026-11-09T15:15:51Z", "fixture_date":"2026-11-22",
        "competition":"Premier League", "home_team":"Liverpool", "away_team":"Man United",
        "ah_line":-0.75,"ah_home_odds":1.925,"ah_away_odds":1.925,
        "asian_line":3.0,"asian_over_odds":1.825,"asian_under_odds":2.025,
        "fixed_over_odds":1.53,"fixed_under_odds":2.5,
        "ah_status":"FORECAST","ah_direction":"HOME","ah_stake_u":1.0,
        "ou_status":"FORECAST","ou_direction":"UNDER","ou_stake_u":1.0,
        "policy_version":"PUBLIC_V2_AH_A_OU_B_REVERSED_1U",
    }


def test_public_feed_path_and_command(tmp_path):
    source=tmp_path/'football_market_analytics_v2_2/public_data/receipt_exports/test.json'
    source.parent.mkdir(parents=True)
    source.write_bytes(archive_json([sample()]))
    file=validate_feed_path(source)
    cmd=prepare_command(file,kickoff='2026-11-22T16:30:00Z',fixture_date='2026-11-22',
        competition='Premier League',kickoff_basis='Official fixtures',
        quote_source='User entered odds; capture unverified',publish=False)
    assert cmd[-1]=='User entered odds; capture unverified'
    assert '--publish' not in cmd
    assert '--archive' in cmd
    assert '--record-id' not in cmd
    assert prepare_command(file,kickoff='2026-11-22T16:30:00Z',fixture_date='2026-11-22',
        competition='Premier League',kickoff_basis='Official fixtures',
        quote_source='User entered odds; capture unverified',publish=True)[-1]=='--publish'


def test_bridge_dry_run_against_existing_p8_1e(tmp_path):
    source=tmp_path/'football_market_analytics_v2_2/public_data/receipt_exports/test.json'
    source.parent.mkdir(parents=True)
    source.write_bytes(archive_json([sample()]))
    cp=subprocess.run([sys.executable,str(ROOT/'scripts/publish_local_public_receipt.py'),
      '--feed',str(source),'--fixture-date','2026-11-22','--competition','Premier League',
      '--kickoff-utc','2026-11-22T16:30:00Z','--kickoff-basis','Official fixtures',
      '--quote-source','User entered; capture unverified'],capture_output=True,text=True,cwd=ROOT)
    assert cp.returncode == 0, cp.stderr
    assert 'DRY RUN: no GitHub Issue' in cp.stdout


def test_rejects_wrong_project_and_symlink(tmp_path):
    wrong=tmp_path/'private_data'/'receipt_exports'/'foo.json'
    wrong.parent.mkdir(parents=True)
    wrong.write_bytes(archive_json([sample()]))
    with pytest.raises(BridgeBlocked): validate_feed_path(wrong)
    target=tmp_path/'football_market_analytics_v2_2/public_data/receipt_exports/test.json'
    target.parent.mkdir(parents=True)
    target.symlink_to(wrong)
    with pytest.raises(BridgeBlocked): validate_feed_path(target)


def test_refuse_wrong_fixture_or_date(tmp_path):
    source=tmp_path/'football_market_analytics_v2_2/public_data/receipt_exports/test.json'
    source.parent.mkdir(parents=True)
    source.write_bytes(archive_json([sample()]))
    with pytest.raises(BridgeBlocked):
        prepare_command(source,kickoff='2026-11-22T16:30:00Z',fixture_date='2026-11-23',
          competition='Premier League',kickoff_basis='x',quote_source='x',publish=False)
    with pytest.raises(BridgeBlocked):
        prepare_command(source,kickoff='2026-11-22T16:30:00Z',fixture_date='2026-11-22',
          competition='Bundesliga',kickoff_basis='x',quote_source='x',publish=False)
