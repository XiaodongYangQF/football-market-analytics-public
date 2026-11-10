"""Independent tests of the combined research history and its public table."""
from copy import deepcopy
from pathlib import Path
import math

import pytest

from fma_portfolio.metrics import summarize
from fma_portfolio.release import load_release
from fma_portfolio.unified_history import (
    UnifiedHistoryError, combine_records, filter_fixture_table, fixture_table_rows,
    load_unified_history, table_page, tracked_fixtures,
)
from fma_portfolio.daily_publish import validate_settlements

ROOT = Path(__file__).resolve().parents[1]


def test_combined_initial_snapshot_is_fully_reconciled():
    latest, combined = load_unified_history(ROOT)
    old = summarize(latest['records'])
    assert len(latest['records']) == 67
    assert old['settled_signals'] == 34
    assert math.isclose(old['pnl_u'], 3.8)
    assert tracked_fixtures(latest['records']) == 33
    history = load_release(ROOT / 'data/historical_replay.json')
    validate_settlements(history)
    assert len(history['records']) == 68
    assert tracked_fixtures(history['records']) == 48
    assert all(r['state'] == 'SETTLED' and r['stake_u'] == 1 for r in history['records'])
    stats = summarize(combined)
    assert len(combined) == 135  # 68 historical + 67 current V2 records (including no signals)
    assert stats['settled_signals'] == 102
    assert math.isclose(stats['turnover_u'], 102)
    assert math.isclose(stats['pnl_u'], 22.9125)
    assert math.isclose(stats['roi_pct'], 22.9125 / 102 * 100)
    assert tracked_fixtures(combined) == 81
    assert stats['fixture_count'] == 72  # settled-signal fixtures, a different metric
    assert len({r['record'] for r in combined}) == len(combined)


def test_market_aggregates_add_up_without_fixed25_signals():
    _, combined = load_unified_history(ROOT)
    ah = summarize(r for r in combined if r['market'] == 'AH')
    ou = summarize(r for r in combined if r['market'] == 'OU')
    assert ah['settled_signals'] == 46 and math.isclose(ah['pnl_u'], 9.0625)
    assert ou['settled_signals'] == 56 and math.isclose(ou['pnl_u'], 13.85)
    assert math.isclose(ah['pnl_u'] + ou['pnl_u'], 22.9125)


def test_public_fixture_market_overrides_history_without_losing_multiple_public_lines():
    latest, _ = load_unified_history(ROOT)
    target = [r for r in latest['records'] if r['fixture'] == 'FC Koln vs Leverkusen' and r['market'] == 'OU']
    assert len(target) == 2 and {r['line'] for r in target} == {2.75, 3.0}
    older = deepcopy(target[0]); older['record'] = 'HR-COLLISION'
    older['line'] = 3.5; older['decimal_odds'] = 1.99
    combined = combine_records([older], target)
    assert {r['record'] for r in combined} == {r['record'] for r in target}
    # When another fixture is introduced on a later day, it should be retained.
    another = deepcopy(older); another['fixture'] = 'Different Fixture'; another['record'] = 'HR-OTHER'
    assert len(combine_records([older, another], target)) == 3


def test_one_fixture_per_row_and_twice_recorded_quote_visible():
    _, combined = load_unified_history(ROOT)
    fixtures = fixture_table_rows(combined)
    assert len(fixtures) == 81
    koln = [r for r in fixtures if r['Fixture'] == 'FC Koln vs Leverkusen']
    assert len(koln) == 1
    assert 'OVER 2.75' in koln[0]['OU forecast · 1u']
    assert 'OVER 3' in koln[0]['OU forecast · 1u']
    assert 'HALF_WIN +0.4000u' in koln[0]['OU result']
    assert 'PUSH +0.0000u' in koln[0]['OU result']
    assert koln[0]['Final score'] == '1–2'
    assert koln[0]['1X2'] == 'AWAY'


def test_missing_market_is_not_invented_no_signal():
    _, combined = load_unified_history(ROOT)
    fixtures = fixture_table_rows(combined)
    early_missing = [r for r in fixtures if r['Date'] < '2026-11-07'
                     and (r['AH forecast · 1u'] == '—' or r['OU forecast · 1u'] == '—')]
    assert early_missing
    assert any(r['AH forecast · 1u'] == '—' for r in early_missing)
    no_signal_rows = [r for r in fixtures if 'NO SIGNAL' in r['AH forecast · 1u'] or 'NO SIGNAL' in r['OU forecast · 1u']]
    assert no_signal_rows
    assert any('NOT RECORDED' in r['AH forecast · 1u'] for r in fixtures)


def test_ledger_filter_sort_and_safe_pagination():
    _, combined = load_unified_history(ROOT)
    fixtures = fixture_table_rows(combined)
    results = filter_fixture_table(fixtures, query='Koln', result_status='Finished')
    assert results
    assert all('koln' in r['Fixture'].casefold() for r in results)
    assert results == sorted(results, key=lambda r: (r['Date'], r['Fixture']), reverse=True)
    old = filter_fixture_table(fixtures, sort_by='Oldest first')
    assert old[0]['Date'] <= old[-1]['Date']
    page, current, pages = table_page(old, 1, 20)
    assert len(page) == 20 and current == 1 and pages == 5
    last, number, _ = table_page(old, 300, 20)
    assert number == 5 and len(last) == 1
    with pytest.raises(ValueError):
        table_page(old, 1, 0)


def test_conflicting_final_scores_block_rendering():
    _, combined = load_unified_history(ROOT)
    old = deepcopy(combined[0]); new = deepcopy(old)
    old.update(record='R1', final_score='2–1')
    new.update(record='R2', final_score='0–3', market='OU')
    with pytest.raises(UnifiedHistoryError, match='Conflicting scores'):
        fixture_table_rows([old, new])


def test_public_history_does_not_modify_daily_public_snapshot():
    script = (ROOT / 'scripts/update_public_performance.py').read_text()
    assert 'data/historical_replay.json' not in script
    # The historical file is a static research artifact, not a prospective receipt.
    app = (ROOT / 'app.py').read_text()
    assert 'current_public_rows' in app
    assert 'reconcile_public_settlement(r, "AH", current_public_rows)' in app
    assert 'Historical forecast ledger' in app
    assert 'Find a fixture' in app and 'Rows per page' in app
    assert 'load_unified_history(ROOT)' in app
