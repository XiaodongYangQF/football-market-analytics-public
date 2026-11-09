"""P7.3 read-only, self-contained fixture reader for Public Web Edition.

The published CSV is an explicit public-data snapshot. Canonical scientific
names may be exported from Local Public, but no private registry or research
files are loaded by the web visitor process.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

LEAGUES = frozenset({'E0', 'D1', 'SP1', 'I1', 'F1'})
FIELDS = ('league','fixture_date','home_team','away_team',
          'canonical_home_team','canonical_away_team')


def _valid(value: object) -> str:
    text = str(value or '').strip()
    if not 1 <= len(text) <= 100 or any(ord(ch) < 32 for ch in text):
        raise ValueError('Invalid public fixture team')
    return text


def load_fixtures(path: Path, league: str) -> list[dict]:
    """Read allowlisted fixture fields; never include untrusted CSV columns."""
    if league not in LEAGUES:
        raise ValueError('Unsupported competition')
    if not path.is_file():
        return []
    if path.stat().st_size > 8_000_000:
        raise ValueError('Fixture file too large')
    out = {}
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        required = {'league','fixture_date','home_team','away_team'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Invalid public fixture CSV')
        for line_number,row in enumerate(reader, 2):
            if row.get('league') != league:
                continue
            try:
                when = date.fromisoformat(str(row['fixture_date']))
                home = _valid(row.get('home_team'))
                away = _valid(row.get('away_team'))
                canonical_home = _valid(row.get('canonical_home_team') or home)
                canonical_away = _valid(row.get('canonical_away_team') or away)
                if home.casefold() == away.casefold() or canonical_home.casefold() == canonical_away.casefold():
                    raise ValueError('Duplicate fixture team')
            except (TypeError,ValueError) as exc:
                raise ValueError(f'Invalid fixture row {line_number}') from exc
            key = (when.isoformat(),home,away)
            out[key] = {'league':league,'fixture_date':when.isoformat(),
                        'home':home,'away':away,
                        'canonical_home':canonical_home,'canonical_away':canonical_away}
            if len(out) > 3000:
                raise ValueError('Too many fixtures in one competition')
    return [out[key] for key in sorted(out)]


def fixture_options(rows: list[dict], window: str, today: date) -> list[dict]:
    if window not in ('Upcoming','All'):
        raise ValueError('Unknown fixture window')
    return [r for r in rows if window == 'All' or r['fixture_date'] >= today.isoformat()]


def team_options(rows: list[dict]) -> list[tuple[str,str]]:
    """List fixed, exported team options as (display, model-name)."""
    lookup = {}
    for row in rows:
        for side in ('home','away'):
            display = row[side]
            canonical = row['canonical_'+side]
            if display in lookup and lookup[display] != canonical:
                raise ValueError('Inconsistent published team mapping')
            lookup[display] = canonical
    return [(label,lookup[label]) for label in sorted(lookup,key=str.casefold)]
