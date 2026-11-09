"""P8.1D data-only update; no Private access, no non-consensual Git push."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from fma_portfolio.daily_publish import (
    ReleaseBlocked, audit_transition, make_manifest, validate_settlements,
)
from fma_portfolio.release import load_release
from fma_portfolio.settlement import settle

ROOT = Path(__file__).resolve().parents[1]
BASE = load_release(ROOT / 'data/public_v2.json')


def _fresh():
    return copy.deepcopy(BASE)


def _new_record(fixture='Sample Home vs Sample Away', market='OU', side='OVER',
                state='SETTLED', score='2–1', odds=1.95, line=2.5):
    outcome, pnl = settle(market, side, line, odds, score)
    return {
        'record': f'V2-SAMPLE-{fixture.replace(" ", "_")}-{market}',
        'source_date': '2026-11-09', 'competition': 'Premier League',
        'fixture': fixture, 'market': market, 'direction': side,
        'line': line, 'decimal_odds': odds, 'stake_u': 1.0,
        'final_score': score if state == 'SETTLED' else None,
        'state': state, 'settlement': outcome if state == 'SETTLED' else None,
        'pnl_u': pnl if state == 'SETTLED' else None, 'price_evidence': 'FROZEN_EXECUTION',
    }


def test_noop_on_identical_content():
    x = _fresh()
    d = audit_transition(x, x)
    assert not d.changed and d.new_signal_count == 0


def test_new_settled_signal_is_added_and_checked():
    old, new = _fresh(), _fresh()
    new['records'].append(_new_record())
    d = audit_transition(old, new)
    assert d.changed and d.new_settlement_count == 1 and d.new_signal_count == 1


def test_already_published_signal_cannot_disappear():
    old, new = _fresh(), _fresh()
    old['records'].append(_new_record())
    with pytest.raises(ReleaseBlocked, match='signal disappeared'):
        audit_transition(old, new)


def test_already_published_quote_cannot_change():
    old, new = _fresh(), _fresh()
    old['records'].append(_new_record())
    new['records'].append(_new_record(odds=2.05))
    with pytest.raises(ReleaseBlocked, match='signal disappeared'):
        audit_transition(old, new)


def test_settled_score_cannot_be_silently_revised():
    old, new = _fresh(), _fresh()
    old['records'].append(_new_record())
    new['records'].append(_new_record(score='1–0'))
    with pytest.raises(ReleaseBlocked, match='settled result changed'):
        audit_transition(old, new)


def test_wrong_pnl_is_rejected():
    r = _new_record()
    r['pnl_u'] = 10
    new = _fresh()
    new['records'].append(r)
    with pytest.raises(ReleaseBlocked, match='arithmetic'):
        validate_settlements(new)


def test_published_no_signal_can_upgrade_to_real_signal():
    old, new = _fresh(), _fresh()
    placeholder = _new_record(state='NO_SIGNAL')
    placeholder.update(direction='NO SIGNAL', decimal_odds=None, stake_u=None,
                       final_score=None, settlement=None, pnl_u=None,
                       price_evidence='MODEL_ONLY')
    old['records'].append(placeholder)
    new['records'].append(_new_record())
    d = audit_transition(old, new)
    assert len(d.placeholder_replacements) == 1 and d.new_signal_count == 1


def test_unexplained_no_signal_disappearance_is_rejected():
    old, new = _fresh(), _fresh()
    placeholder = _new_record(state='NO_SIGNAL')
    placeholder.update(direction='NO SIGNAL', decimal_odds=None, stake_u=None,
                       final_score=None, settlement=None, pnl_u=None)
    old['records'].append(placeholder)
    with pytest.raises(ReleaseBlocked, match='placeholder disappeared'):
        audit_transition(old, new)


def test_manifest_contains_only_public_counts_not_paths():
    x = make_manifest(BASE, 'e' * 64, released_at_utc='2026-11-09T09:00:00Z')
    assert x['settled_signals'] == sum(r['state'] == 'SETTLED' for r in BASE['records'])
    import math
    assert math.isclose(x['pnl_u'], sum(float(r['pnl_u']) for r in BASE['records']
                                              if r['state'] == 'SETTLED'), abs_tol=1e-8)
    assert x['source_public_snapshot_sha256'] == 'e' * 64
    assert 'Private' not in str(x)
    assert 'runtime_data' not in str(x)


def test_daily_script_does_not_import_private_ledgers():
    code = (ROOT / 'scripts/update_public_performance.py').read_text()
    assert 'runtime_data' not in code
    assert 'postmatch_results.jsonl' not in code
    assert 'simulated_trades_v1.jsonl' not in code
