"""Public-only history composition and a fixture-oriented read-only ledger.

Historical replay is kept as an explicit separate data asset for internal
reconciliation. The public view combines it with the normal Local Public V2
release, while preserving all explicit NO SIGNAL and NOT_RECORDED outcomes.
The normal daily publishing pipeline updates only public_v2.json and must not
rewrite this historical replay or treat it as a prospective receipt.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from fma_portfolio.daily_publish import validate_settlements
from fma_portfolio.release import load_release
from fma_portfolio.settlement import SCORE_PATTERN


class UnifiedHistoryError(ValueError):
    """Stored public history is inconsistent or ambiguous."""


def market_key(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return tuple(str(row[k]) for k in ('source_date', 'competition', 'fixture', 'market'))


def fixture_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return tuple(str(row[k]) for k in ('source_date', 'competition', 'fixture'))


def combine_records(historical: Iterable[Mapping[str, Any]],
                    recorded: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Use the normal public release as authoritative on overlapping markets.

    A published fixture-market may legitimately contain multiple saved quotes
    (e.g. two OU lines). Keep every distinct public record; never collapse it
    into one signal or silently count a historical replay in addition.
    """
    published = [dict(r) for r in recorded]
    archived = [dict(r) for r in historical]
    public_markets = {market_key(r) for r in published}
    selected = [r for r in archived if market_key(r) not in public_markets]
    result = selected + published
    identifiers = [r['record'] for r in result]
    if len(identifiers) != len(set(identifiers)):
        raise UnifiedHistoryError('Duplicate public forecast record IDs')
    return sorted(result, key=lambda r: (
        r['source_date'], r['competition'], r['fixture'], r['market'], r['record']))


def load_unified_history(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (current-day public release, combined curated records)."""
    latest = load_release(root / 'data' / 'public_v2.json')
    archived = load_release(root / 'data' / 'historical_replay.json')
    validate_settlements(latest)
    validate_settlements(archived)
    if any(r['state'] != 'SETTLED' for r in archived['records']):
        raise UnifiedHistoryError('Historical replay must contain settled records only')
    return latest, combine_records(archived['records'], latest['records'])


def tracked_fixtures(rows: Iterable[Mapping[str, Any]]) -> int:
    return len({fixture_key(r) for r in rows})


def _line_label(row: Mapping[str, Any]) -> str:
    line = row.get('line')
    if line is None:
        return '—'
    number = float(line)
    if row['market'] == 'AH':
        return f'{number:+g}' if number != 0 else '0'
    return f'{number:g}'


def _forecast_label(row: Mapping[str, Any]) -> str:
    state = row['state']
    if state == 'NO_SIGNAL':
        return 'NO SIGNAL'
    if state == 'NOT_RECORDED':
        return 'NOT RECORDED'
    direction = row['direction']
    if direction == 'NO SIGNAL':
        return 'NO SIGNAL'
    stake = row.get('stake_u')
    amount = '1u' if stake == 1 else (f'{stake:g}u' if stake else 'stake unavailable')
    return f'{direction} {_line_label(row)} · {amount}'


def _result_label(row: Mapping[str, Any]) -> str:
    if row['state'] != 'SETTLED':
        return '—'
    profit = float(row['pnl_u'])
    return f"{row['settlement']} {profit:+.4f}u"


def fixture_table_rows(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One fixture per row; preserve multiple quote observations in a cell.

    An entirely absent market means missing evidence, *not* NO SIGNAL.
    Conflicting final scores on the same fixture block the table.
    """
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        grouped[fixture_key(r)].append(dict(r))
    items = []
    for (date, competition, fixture), family in sorted(grouped.items(), reverse=True):
        scores = {str(r['final_score']) for r in family if r.get('final_score')}
        parsed = set()
        for score in scores:
            match = SCORE_PATTERN.fullmatch(score)
            if match is None:
                raise UnifiedHistoryError(f'Unrecognized recorded final score: {score}')
            parsed.add((int(match.group(1)), int(match.group(2))))
        if len(parsed) > 1:
            raise UnifiedHistoryError(f'Conflicting scores for {date} | {competition} | {fixture}')
        if parsed:
            home, away = next(iter(parsed))
            result = 'HOME' if home > away else 'AWAY' if home < away else 'DRAW'
            score = f'{home}–{away}'
            status = 'Finished'
        else:
            score, result, status = '—', '—', 'Result pending'
        table_row = {
            'Date': date,
            'Competition': competition,
            'Fixture': fixture,
            'Final score': score,
            'Match status': status,
            '1X2': result,
        }
        for market in ('AH', 'OU'):
            selected = [r for r in family if r['market'] == market]
            # Different published lines are separate observations, not
            # unintentional duplicate entries or duplicate fixture rows.
            selected.sort(key=lambda r: (
                r['line'] is None, str(r['line']), str(r['record'])))
            table_row[f'{market} forecast · 1u'] = ' | '.join(_forecast_label(r) for r in selected) if selected else '—'
            table_row[f'{market} result'] = ' | '.join(_result_label(r) for r in selected) if selected else '—'
        items.append(table_row)
    return items


def filter_fixture_table(items: Iterable[Mapping[str, Any]], *, query: str = '',
                         result_status: str = 'All statuses',
                         sort_by: str = 'Newest first') -> list[dict[str, Any]]:
    query = query.strip().casefold()
    matched = [dict(r) for r in items
               if (not query or query in str(r['Fixture']).casefold()
                   or query in str(r['Competition']).casefold())
               and (result_status == 'All statuses' or r['Match status'] == result_status)]
    if sort_by == 'Oldest first':
        return sorted(matched, key=lambda r: (r['Date'], r['Fixture']))
    if sort_by == 'Fixture A–Z':
        return sorted(matched, key=lambda r: (r['Fixture'].casefold(), r['Date']))
    if sort_by != 'Newest first':
        raise ValueError(f'Unsupported table sort: {sort_by}')
    return sorted(matched, key=lambda r: (r['Date'], r['Fixture']), reverse=True)


def table_page(items: list[dict[str, Any]], page: int, size: int) -> tuple[list[dict[str, Any]], int, int]:
    if size <= 0:
        raise ValueError('Page size must be positive')
    count = len(items)
    pages = max(1, (count + size - 1) // size)
    page = min(max(int(page), 1), pages)
    return items[(page - 1) * size: page * size], page, pages
