"""P8.1E provider-time proof and tamper controls, without remote network calls."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid
import pytest

from fma_portfolio.p7.saved_forecasts import create_record, archive_json
from fma_portfolio.prematch_receipts import (
    REPO_ISSUES, ReceiptError, batch_from_issue_body, body_for_issue,
    make_batch, make_receipt, read_receipts, receipt_path, validate_batch,
    validate_receipt,
)


def forecast(home='Köln', away='Leverkusen', *, when="2026-11-14", minute=20):
    request = {'league': 'D1', 'home': home, 'away': away, 'fixture_date': when,
               'ah_line': 0.25, 'ah_home_odds': 1.92, 'ah_away_odds': 1.9,
               'asian_line': 2.75, 'asian_over_odds': 1.95, 'asian_under_odds': 1.85,
               'fixed_over_odds': 1.91, 'fixed_under_odds': 1.94}
    result = {'ah': {'status': 'NO_SIGNAL', 'direction': None, 'stake_u': None},
              'ou': {'status': 'FORECAST', 'direction': 'UNDER', 'stake_u': 1.0}}
    return create_record(request, result, competition='Bundesliga',
                         display_home=home, display_away=away,
                         now=datetime(2026,11,14,14,minute,tzinfo=timezone.utc),
                         record_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f'{home}:{away}:{minute}')))


def batch():
    return make_batch([forecast()], '2026-11-14T14:30:00Z')


def github_issue(batch_obj, created_at='2026-11-14T14:27:02Z', number=12):
    return {'number': number, 'html_url': REPO_ISSUES + str(number),
            'created_at': created_at, 'body': body_for_issue(batch_obj)}


def test_all_input_odds_and_both_market_outputs_survive_and_hash_is_stable():
    a = batch()
    assert make_batch([forecast()], '2026-11-14T14:30:00+00:00') == a
    assert a['records'][0]['fixed_under_odds'] == 1.94
    assert a['records'][0]['ah_status'] == 'NO_SIGNAL'
    assert a['records'][0]['ou_direction'] == 'UNDER'
    assert batch_from_issue_body(body_for_issue(a)) == a


def test_multiple_fixtures_one_provider_timestamp_batch():
    rows = [forecast('Bayern', 'Mainz'), forecast('Köln', 'Leverkusen')]
    data = make_batch(rows, '2026-11-14T14:30:00Z')
    assert len(data['records']) == 2
    assert data['records'] == sorted(data['records'], key=lambda r:(r['competition'], r['home_team'], r['away_team'], r['record_id']))


def test_reject_generated_at_kickoff_and_duplicate_fixture():
    with pytest.raises(ReceiptError, match='on/after'):
        make_batch([forecast(minute=30)], '2026-11-14T14:30:00Z')
    with pytest.raises(ReceiptError, match='Duplicate'):
        make_batch([forecast(), forecast()], '2026-11-14T14:30:00Z')


def test_reject_outside_declared_fixture_day_and_too_many():
    with pytest.raises(ReceiptError):
        make_batch([forecast(when='2026-11-07')], '2026-11-14T14:30:00Z')
    with pytest.raises(ReceiptError):
        make_batch([forecast(f'Team{i}', f'Rival{i}') for i in range(17)], '2026-11-14T14:30:00Z')


def test_content_or_digest_cannot_change_unnoticed():
    a = batch()
    changed = deepcopy(a)
    changed['records'][0]['ou_direction'] = 'OVER'
    with pytest.raises(ReceiptError):
        validate_batch(changed)
    with pytest.raises(ReceiptError):
        batch_from_issue_body(body_for_issue(a).replace('UNDER', 'OVER'))
    with pytest.raises(ReceiptError):
        batch_from_issue_body(body_for_issue(a).replace('json', 'text', 1))


def test_remote_created_at_before_declared_kickoff_and_late_are_distinct():
    a = batch()
    early = make_receipt(a, github_issue(a), checked_at='2026-11-14T14:27:03Z')
    assert early['publication_class'] == 'ON_TIME_DECLARED'
    late = make_receipt(a, github_issue(a, '2026-11-14T14:30:01Z'),
                        checked_at='2026-11-14T14:30:02Z')
    assert late['publication_class'] == 'LATE_PUBLICATION'
    tampered = deepcopy(early)
    tampered['publication_class'] = 'ON_TIME_VERIFIED'
    with pytest.raises(ReceiptError):
        validate_receipt(tampered)


def test_changed_issue_body_and_wrong_repository_rejected():
    a = batch()
    issue = github_issue(a)
    issue['body'] += ' edited'
    with pytest.raises(ReceiptError, match='differs'):
        make_receipt(a, issue)
    issue = github_issue(a)
    issue['html_url'] = 'https://github.com/other/other/issues/12'
    with pytest.raises(ReceiptError, match='URL'):
        make_receipt(a, issue)


def test_archives_can_be_read_and_detect_reposted_fixture(tmp_path):
    a = batch()
    receipt = make_receipt(a, github_issue(a), checked_at='2026-11-14T14:27:03Z')
    file = receipt_path(tmp_path, a)
    file.parent.mkdir(parents=True)
    file.write_text(json.dumps(receipt, ensure_ascii=False))
    assert len(read_receipts(tmp_path)) == 1
    bad = deepcopy(receipt)
    bad['batch_sha256'] = '0'*64
    file.write_text(json.dumps(bad))
    with pytest.raises(ReceiptError, match='hash'):
        read_receipts(tmp_path)
    file.write_text(json.dumps(receipt))
    b = make_batch([forecast(minute=21)], '2026-11-14T14:30:00Z')
    second = make_receipt(b, github_issue(b, number=13), checked_at='2026-11-14T14:27:03Z')
    p = receipt_path(tmp_path, b)
    p.write_text(json.dumps(second))
    with pytest.raises(ReceiptError, match='Same fixture'):
        read_receipts(tmp_path)


def test_dry_run_cli_does_not_use_network_or_publish(tmp_path):
    archive = tmp_path / 'export.json'
    archive.write_bytes(archive_json([forecast()]))
    root = Path(__file__).resolve().parents[1]
    call = [sys.executable, str(root/'scripts/publish_prematch_receipt.py'),
            '--archive', str(archive), '--fixture-date', '2026-11-14',
            '--competition', 'Bundesliga', '--kickoff-utc', '2026-11-14T14:30:00Z']
    proc = subprocess.run(call, cwd=root, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr
    assert 'DRY RUN' in proc.stdout and 'Köln vs Leverkusen' in proc.stdout
    no_selection = subprocess.run([sys.executable, str(root/'scripts/publish_prematch_receipt.py'),
            '--archive', str(archive), '--kickoff-utc', '2026-11-14T14:30:00Z'],
            cwd=root, text=True, capture_output=True)
    assert no_selection.returncode != 0
    assert 'selector' in no_selection.stderr


def test_public_app_exposes_archive_separately_from_performance():
    root = Path(__file__).resolve().parents[1]
    app = (root/'app.py').read_text(encoding='utf-8')
    assert 'Pre-match archive' in app and 'read_receipts(ROOT)' in app
    assert 'receipts never enter P&L a second time.' in app


def test_settlement_reconciliation_never_matches_only_by_fixture():
    from fma_portfolio.prematch_receipts import reconcile_public_settlement
    rec = forecast()
    matching = {"source_date": rec["fixture_date"], "competition": "Bundesliga",
                "fixture": "Köln vs Leverkusen", "market": "OU", "direction": "UNDER",
                "line": 2.75, "decimal_odds": 1.85, "stake_u": 1.0,
                "state": "SETTLED", "settlement": "WIN", "pnl_u": 0.85}
    assert reconcile_public_settlement(rec, "OU", [matching]) == "SETTLED: WIN (+0.8500u)"
    changed = dict(matching, decimal_odds=1.88)
    assert reconcile_public_settlement(rec, "OU", [changed]).startswith("UNLINKED")
    assert reconcile_public_settlement(rec, "OU", [matching, matching]).startswith("UNLINKED")


def test_end_to_end_publish_flow_with_fake_github_without_network(tmp_path, monkeypatch, capsys):
    """Exercises the CLI decision path and mirror write; network/commit are faked."""
    from datetime import timedelta
    from scripts import publish_prematch_receipt as cli
    from fma_portfolio.prematch_receipts import stamp
    now = datetime.now(timezone.utc)
    kickoff = now + timedelta(minutes=12)
    rec = forecast(when=now.date().isoformat())
    rec['saved_at_utc'] = stamp((now-timedelta(minutes=2)).isoformat())
    archive = tmp_path / 'source_export.json'
    archive.write_bytes(archive_json([rec]))
    monkeypatch.setattr(cli, 'ROOT', tmp_path)
    monkeypatch.setattr(cli, '_verify_git_ready', lambda **kwargs: None)
    monkeypatch.setattr(cli, '_existing_issue', lambda batch_obj, resume_issue=None: None)
    def api(endpoint, method='GET', fields=None):
        assert method == 'POST' and endpoint.endswith('/issues')
        return {'number': 42, 'html_url': REPO_ISSUES + '42',
                'created_at': stamp(now.isoformat()), 'body': fields['body']}
    monkeypatch.setattr(cli, '_gh_json', api)
    called = []
    def commands(command, timeout=40):
        called.append(command)
        if command[:4] == ['git','diff','--cached','--name-only']:
            return 'data/forecast_receipts/receipt.json'
        if command[:3] == ['git','rev-list','--count']:
            return '1'
        return ''
    monkeypatch.setattr(cli, '_run', commands)
    monkeypatch.setattr(sys, 'argv', ['publish_prematch_receipt.py',
        '--archive', str(archive), '--fixture-date', now.date().isoformat(),
        '--kickoff-utc', stamp(kickoff.isoformat()), '--publish', '--yes'])
    assert cli.main() == 0
    mirror = read_receipts(tmp_path)
    assert len(mirror) == 1 and mirror[0]['github_issue_number'] == 42
    assert mirror[0]['publication_class'] == 'ON_TIME_DECLARED'
    assert any(c[:3] == ['git','push','origin'] for c in called)
    assert 'PUBLIC ISSUE:' in capsys.readouterr().out
