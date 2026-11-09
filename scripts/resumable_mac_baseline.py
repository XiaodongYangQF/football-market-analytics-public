#!/usr/bin/env python3
"""P8.1C-2: private, resumable Mac baseline with per-case progress.

No scientific model, forecast rule, or public dataset is modified. Each
successful case creates one non-overwriting private checkpoint file outside
this public repository. Checkpoint identity and request hashes are checked on
resume; mismatches fail closed. A complete baseline is written ONLY if all
cases succeed. The stdout progress never prints fixture names or market inputs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fma_portfolio.runtime_parity import (
    Roots, ParityError, SCHEMA_BASELINE, canonical, digest_bytes, load_cases,
    private_path, read_json, safe_write_private_json, source_identity,
    validate_baseline,
)
from fma_portfolio.p7.owner_local import (
    ForecastUnavailable, _clean_projection, execute_frozen_worker,
)

CHECKPOINT_SCHEMA = 'FMA_PRIVATE_RUNTIME_CASE_CHECKPOINT_V1'


def fingerprint(identity: dict) -> str:
    return digest_bytes(canonical(identity))


def checkpoint_filename(checkpoint_dir: Path, index: int) -> Path:
    return checkpoint_dir / f'case_{index:03d}.json'


def resume_case(checkpoint: Path, *, index: int, case: dict,
                identity: dict, repo_root: Path) -> dict | None:
    """Return verified saved result or None. Never accept mismatched checkpoints."""
    target = private_path(checkpoint, repo_root, should_exist=False)
    if not target.exists():
        return None
    value = read_json(private_path(target, repo_root, should_exist=True), 1_000_000)
    if not isinstance(value, dict) or set(value) != {
        'schema', 'index', 'identity_sha256', 'request_sha256', 'row'
    }:
        raise ParityError('Checkpoint schema mismatch')
    if (value['schema'] != CHECKPOINT_SCHEMA or value['index'] != index or
        value['identity_sha256'] != fingerprint(identity) or
        value['request_sha256'] != digest_bytes(canonical(case['request']))):
        raise ParityError('Checkpoint input or runtime identity changed')
    row = value['row']
    if not isinstance(row, dict) or set(row) != {
        'id', 'request_sha256', 'result', 'wall_seconds'
    } or row['id'] != case['id'] or row['request_sha256'] != value['request_sha256']:
        raise ParityError('Checkpoint model result changed')
    if type(row['wall_seconds']) not in (int, float) or not 0 <= row['wall_seconds'] < 1_000_000:
        raise ParityError('Invalid checkpoint duration')
    _clean_projection(row['result'])
    return row


def save_case(checkpoint: Path, *, index: int, case: dict, identity: dict,
              result: dict, wall_seconds: float, repo_root: Path) -> dict:
    row = {
        'id': case['id'], 'request_sha256': digest_bytes(canonical(case['request'])),
        'result': _clean_projection(result), 'wall_seconds': round(wall_seconds, 4),
    }
    payload = {
        'schema': CHECKPOINT_SCHEMA, 'index': index,
        'identity_sha256': fingerprint(identity),
        'request_sha256': row['request_sha256'], 'row': row,
    }
    safe_write_private_json(checkpoint, payload, repo_root)
    return row


def make_private_checkpoint_dir(path: Path, repo_root: Path) -> Path:
    target = private_path(path, repo_root, should_exist=False)
    if target.is_symlink():
        raise ParityError('Checkpoint directory may not be a symlink')
    if not target.exists():
        target.mkdir(mode=0o700, parents=False)
    if not target.is_dir() or target.stat().st_mode & 0o077:
        raise ParityError('Checkpoint directory must be owner-only (mode 0700)')
    return target


def process_cases(rows: list[dict], identity: dict, *, checkpoint_dir: Path,
                  repo_root: Path, run_model) -> list[dict]:
    results = []
    total = len(rows)
    for i, case in enumerate(rows, start=1):
        checkpoint = checkpoint_filename(checkpoint_dir, i)
        existing = resume_case(checkpoint, index=i, case=case,
                               identity=identity, repo_root=repo_root)
        if existing is not None:
            print(f'CASE {i}/{total}: CHECKPOINT REUSED ({existing["wall_seconds"]:.2f}s)', flush=True)
            results.append(existing)
            continue
        print(f'CASE {i}/{total}: START', flush=True)
        started = time.perf_counter()
        try:
            projection = run_model(case['request'])
        except ForecastUnavailable as exc:
            # Avoid leaking traceback, worker stdout/stderr, fixture data and full paths.
            cause = 'CASE_TIMEOUT' if isinstance(exc.__cause__, subprocess.TimeoutExpired) else 'WORKER_FAILURE'
            print(f'CASE {i}/{total}: FAILED ({cause}); {len(results)} checkpoints retained', flush=True)
            raise
        elapsed = time.perf_counter() - started
        saved = save_case(checkpoint, index=i, case=case, identity=identity,
                          result=projection, wall_seconds=elapsed, repo_root=repo_root)
        print(f'CASE {i}/{total}: PASS ({elapsed:.2f}s); checkpoint saved', flush=True)
        results.append(saved)
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path.home()/'Projects/football_market_analytics_v2_2')
    parser.add_argument('--science-root', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--model-python', type=Path, default=Path(os.environ.get('FMA_PORTFOLIO_MODEL_PYTHON') or sys.executable))
    parser.add_argument('--reference-root', type=Path, action='append', default=[])
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--baseline-file', type=Path, required=True)
    parser.add_argument('--checkpoint-dir', type=Path, required=True)
    parser.add_argument('--max-case-seconds', type=int, default=120)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.max_case_seconds <= 1200:
            raise ParityError('Invalid case timeout')
        roots = Roots(args.project_root, args.science_root, args.data_root,
                      args.model_python).resolved()
        cases_path = private_path(args.cases, ROOT, should_exist=True)
        baseline_path = private_path(args.baseline_file, ROOT, should_exist=False)
        if baseline_path.exists():
            raise ParityError('Baseline already exists, will not overwrite')
        checkpoint_dir = make_private_checkpoint_dir(args.checkpoint_dir, ROOT)
        identity = source_identity(roots, args.reference_root, ROOT)
        rows = load_cases(cases_path)
        print(f'PRIVATE CASES: {len(rows)}; scientific sources: {len(identity["source_files"])}', flush=True)
        print(f'REFERENCE COVERAGE: {identity["reference_coverage"]}', flush=True)
        print('Case progress contains no teams, input odds or model details.', flush=True)
        worker = roots.project/'deployment/public_web/web_app/model_worker.py'
        def run_model(request):
            return execute_frozen_worker(request, project=roots.project,
                   science=roots.science, data=roots.data, worker=worker,
                   executable=str(roots.model_python), timeout_seconds=args.max_case_seconds)
        output_rows = process_cases(rows, identity, checkpoint_dir=checkpoint_dir,
                                    repo_root=ROOT, run_model=run_model)
        baseline = {
            'schema': SCHEMA_BASELINE,
            'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
            'runtime': identity, 'cases': output_rows,
        }
        validate_baseline(baseline)
        safe_write_private_json(baseline_path, baseline, ROOT)
        print(f'BASELINE CREATED: {len(output_rows)} verified case outputs; stored privately.', flush=True)
        if identity['reference_coverage'] == 'NOT_CAPTURED':
            print('WARNING: reference files NOT captured; not a production promotion result.', flush=True)
        print('NOT A LINUX PARITY RESULT, NOR A PROSPECTIVE FORECAST RECORD.', flush=True)
        return 0
    except (ParityError, ForecastUnavailable, OSError, RuntimeError, TypeError, ValueError) as exc:
        # Output the safe category only; model data/logs and private paths stay private.
        if isinstance(exc, ForecastUnavailable):
            category = 'MODEL_EXECUTION_FAILURE'
        elif isinstance(exc, ParityError):
            category = 'PRIVATE_EVIDENCE_OR_IDENTITY_FAILURE'
        else:
            category = 'RUNTIME_OR_IO_FAILURE'
        print(f'STOPPED: {category}; successful checkpoints remain available for resume.', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('STOPPED: interrupted by user; completed checkpoints remain available.', file=sys.stderr)
        return 130

if __name__ == '__main__':
    raise SystemExit(main())
