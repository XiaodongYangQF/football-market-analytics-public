#!/usr/bin/env python3
"""Build a PRIVATE P8.1C parity corpus from previously exported Private analysis ZIP.

No model execution, no edits to the Private project, no GitHub publishing.
The generated JSON contains individual market inputs; keep it OUTSIDE GitHub.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fma_portfolio.runtime_parity import (ParityError, SCHEMA_CASES,
    canonical, digest_bytes, private_path, safe_write_private_json)
from fma_portfolio.p7.forecast_contract import validate_request


def cases_from_export(path: Path, *, count: int = 40) -> tuple[list[dict], int]:
    if not 1 <= count <= 96:
        raise ParityError('Count must be between 1 and 96')
    results, rejected, seen = [], 0, set()
    try:
        with zipfile.ZipFile(path) as archive:
            members = sorted((item for item in archive.infolist()
                              if '/Private/analyses/' in item.filename
                              and item.filename.rsplit('/', 1)[-1].startswith('AN_')
                              and item.filename.endswith('.json') and not item.is_dir()),
                             key=lambda item: item.filename)
            if len(members) > 1000:
                raise ParityError('Archive contains too many private analysis snapshots')
            for info in members:
                if info.file_size > 100_000 or info.file_size < 100 or info.compress_size > 100_000:
                    rejected += 1
                    continue
                try:
                    data = json.loads(archive.read(info).decode('utf-8'))
                    if data.get('schema_version') != 'ANALYSIS_SNAPSHOT_V1':
                        raise ValueError
                    fixture = data['fixture']; inputs = data['market_inputs']
                    ah = inputs['ah']; total = inputs['ou_asian_main']; fixed = inputs['ou_fixed25']
                    req = validate_request({
                        'league': fixture['league'], 'home': fixture['home_team'],
                        'away': fixture['away_team'], 'fixture_date': fixture['fixture_date'],
                        'ah_line': ah['line'], 'ah_home_odds': ah['home_or_over_price'],
                        'ah_away_odds': ah['away_or_under_price'],
                        'asian_line': total['line'], 'asian_over_odds': total['home_or_over_price'],
                        'asian_under_odds': total['away_or_under_price'],
                        'fixed_over_odds': fixed['home_or_over_price'],
                        'fixed_under_odds': fixed['away_or_under_price'],
                    })
                    fingerprint = digest_bytes(canonical(req))
                    if fingerprint in seen:
                        continue
                    seen.add(fingerprint)
                    results.append({'id':data['analysis_id'], 'request':req})
                except (ValueError, TypeError, KeyError, AttributeError):
                    rejected += 1
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise ParityError('Unable to read Private analysis export') from exc
    if not results:
        raise ParityError('No valid Private analysis snapshots in archive')
    # Deterministic league-balanced round robin over already saved real inputs.
    leagues = ('E0', 'D1', 'SP1', 'I1', 'F1')
    buckets = {league: [] for league in leagues}
    for row in results:
        buckets[row['request']['league']].append(row)
    chosen = []
    while len(chosen) < count and any(buckets.values()):
        for league in leagues:
            if buckets[league] and len(chosen) < count:
                chosen.append(buckets[league].pop(0))
    return chosen, rejected



def _safe_failure_reason(exc: Exception, source: Path, target: Path) -> str:
    """Actionable, non-sensitive category; never echo exception paths or input data."""
    if not source.is_file():
        return 'SOURCE_MISSING: --analysis-export does not point to an existing readable ZIP. Check the exact Downloads filename.'
    if not zipfile.is_zipfile(source):
        return 'SOURCE_NOT_ZIP: --analysis-export is not a valid ZIP archive.'
    if target.exists():
        return 'OUTPUT_EXISTS: --output already exists. Existing private evidence is never overwritten; choose a new output filename.'
    if not target.parent.is_dir():
        return 'OUTPUT_PARENT_MISSING: create the private output directory before running this command.'
    safe_messages = {
        'Private evidence path must be OUTSIDE the public GitHub repository':
            'PUBLIC_ROOT_FORBIDDEN: keep the analysis ZIP and private output outside the GitHub repository.',
        'Symlinks are not permitted for private evidence':
            'SYMLINK_FORBIDDEN: use a real file path, not a symbolic link.',
        'No valid Private analysis snapshots in archive':
            'NO_VALID_SNAPSHOTS: ZIP has no compatible Private analysis snapshots.',
        'Archive contains too many private analysis snapshots':
            'SOURCE_TOO_LARGE: ZIP contains too many Private analysis snapshots.',
        'Unable to read Private analysis export':
            'SOURCE_READ_ERROR: cannot read analysis ZIP safely.',
        'Existing private evidence cannot be overwritten':
            'OUTPUT_EXISTS: private baseline evidence cannot be overwritten.',
        'Count must be between 1 and 96':
            'COUNT_INVALID: --count must be between 1 and 96.',
        'Private evidence too large':
            'OUTPUT_TOO_LARGE: extracted evidence exceeds the private output size cap.',
    }
    if isinstance(exc, ParityError):
        return safe_messages.get(str(exc), 'PRIVATE_EVIDENCE_VALIDATION_FAILED: private evidence safety check failed.')
    if isinstance(exc, PermissionError):
        return 'PERMISSION_DENIED: check read access to the ZIP and write access to the private output directory.'
    return 'IO_ERROR: could not read or write the private evidence safely; check filesystem permissions.'

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-export', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--count', type=int, default=40)
    args=parser.parse_args(argv)
    try:
        source = private_path(args.analysis_export, ROOT, should_exist=True)
        target = private_path(args.output, ROOT, should_exist=False)
        cases,rejected = cases_from_export(source, count=args.count)
        safe_write_private_json(target, {'schema':SCHEMA_CASES,'cases':cases}, ROOT)
    except (ParityError, OSError, ValueError) as exc:
        # The original generic STOPPED message masked common problems on macOS.
        # Do not print raw OSError: it can expose private paths or filenames.
        print('STOPPED: private analysis extraction could not complete safely.', file=sys.stderr)
        print('REASON: ' + _safe_failure_reason(exc, args.analysis_export, args.output), file=sys.stderr)
        return 2
    counts={league:sum(row['request']['league']==league for row in cases)
            for league in ('E0','D1','SP1','I1','F1')}
    print(f'PRIVATE PARITY CORPUS CREATED: {len(cases)} distinct historical model inputs; {rejected} rejected source rows')
    print('By league:', ', '.join(f'{k}={v}' for k,v in counts.items()))
    print('Evidence stays outside GitHub. Historical test cases do NOT count as prospective forecasts.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
