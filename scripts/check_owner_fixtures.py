#!/usr/bin/env python3
"""Read-only diagnostic for owner-local P7 Public fixture data (never exports it)."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fma_portfolio.p7.fixture_source import fixture_source
from fma_portfolio.p7.fixtures_store import load_fixtures, fixture_options

LEAGUES = {'Premier League': 'E0', 'Bundesliga': 'D1', 'La Liga': 'SP1',
           'Serie A': 'I1', 'Ligue 1': 'F1'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path,
                        default=Path.home() / 'Projects' / 'football_market_analytics_v2_2')
    args = parser.parse_args(argv)
    source, local = fixture_source(ROOT / 'data' / 'fixtures.csv', owner_local=True,
                                   project_root=str(args.project_root))
    if not local:
        print('STOPPED: original P7 Public fixtures.csv not found:',
              args.project_root / 'deployment/public_web/data/fixtures.csv', file=sys.stderr)
        return 2
    print('Owner-local P7 Public fixtures:', source)
    today = date.today()
    total = 0
    try:
        for name, league in LEAGUES.items():
            rows = load_fixtures(source, league)
            upcoming = fixture_options(rows, 'Upcoming', today)
            total += len(rows)
            next_date = upcoming[0]['fixture_date'] if upcoming else 'none'
            print(f'{name:17s} total={len(rows):4d} upcoming={len(upcoming):4d} next={next_date}')
    except (OSError, ValueError) as exc:
        print(f'STOPPED: malformed local P7 schedule: {exc}', file=sys.stderr)
        return 2
    if total == 0:
        print('STOPPED: P7 Public schedule contains no fixtures', file=sys.stderr)
        return 2
    print('OK:', total, 'fixtures available on this Mac; no files modified.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
