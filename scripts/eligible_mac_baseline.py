#!/usr/bin/env python3
"""Season-gated, resumable PRIVATE parity baseline, preserving original case indices.

Use the EXISTING 40-case corpus and checkpoint directory. Promoted-team
fixtures remain in coverage evidence but are NEVER sent to the scientific
worker. Outputs are a filtered eligible case corpus and a compatible baseline
for later Mac/Linux parity. Never publish generated private evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
import time
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fma_portfolio.eligibility import POLICY_PATH, classify_fixture, load_policy, EligibilityPolicyError
from fma_portfolio.runtime_parity import (
    Roots, ParityError, SCHEMA_BASELINE, SCHEMA_CASES, canonical, digest_bytes, digest_file,
    load_cases, private_path, safe_write_private_json, source_identity, validate_baseline,
)
from fma_portfolio.p7.owner_local import ForecastUnavailable, execute_frozen_worker
from scripts.resumable_mac_baseline import (
    checkpoint_filename, make_private_checkpoint_dir, resume_case, save_case,
)

SCHEMA_COVERAGE = 'FMA_PRIVATE_ELIGIBILITY_COVERAGE_V1'


def plan(rows: list[dict], policy: dict) -> tuple[list, list, list]:
    eligible, excluded, unverified = [], [], []
    for index, row in enumerate(rows, 1):
        req = row['request']
        decision = classify_fixture(req['league'],req['home'],req['away'],req['fixture_date'],policy=policy)
        entry = {'index':index,'id':row['id'],
                 'request_sha256':digest_bytes(canonical(req)),
                 'status':decision.status,'reason':decision.reason}
        if decision.status == 'ELIGIBLE':
            eligible.append((index,row))
        elif decision.status == 'INELIGIBLE':
            excluded.append(entry)
        else:
            unverified.append(entry)
    return eligible, excluded, unverified


def run_eligible(eligible: list[tuple[int,dict]], identity: dict, *, checkpoint_dir: Path,
                 repo_root: Path, run_model) -> list[dict]:
    """Reuse checkpoint_NNN by ORIGINAL position, not filtered position."""
    outputs=[]
    for index, case in eligible:
        cp = checkpoint_filename(checkpoint_dir,index)
        existing = resume_case(cp,index=index,case=case,identity=identity,repo_root=repo_root)
        if existing is not None:
            print(f'CASE {index}: CHECKPOINT REUSED',flush=True)
            outputs.append(existing)
            continue
        print(f'CASE {index}: START',flush=True)
        start=time.perf_counter()
        try:
            result=run_model(case['request'])
        except ForecastUnavailable as exc:
            reason = ('CASE_TIMEOUT' if isinstance(exc.__cause__,subprocess.TimeoutExpired)
                      else 'WORKER_FAILURE')
            print(f'CASE {index}: FAILED ({reason}); previous checkpoints retained',flush=True)
            raise
        elapsed=time.perf_counter()-start
        row=save_case(cp,index=index,case=case,identity=identity,result=result,
                      wall_seconds=elapsed,repo_root=repo_root)
        print(f'CASE {index}: PASS ({elapsed:.2f}s); checkpoint saved',flush=True)
        outputs.append(row)
    return outputs


def coverage_doc(rows: list[dict], eligible: list, excluded: list, unverified: list,
                 policy_sha256: str) -> dict:
    return {
        'schema':SCHEMA_COVERAGE,
        'policy_sha256':policy_sha256,
        'original_corpus_sha256':digest_bytes(canonical(rows)),
        'original_case_count':len(rows),
        'eligible_count':len(eligible),
        'excluded_count':len(excluded),
        'unverified_count':len(unverified),
        'excluded':excluded,
        'unverified':unverified,
        'note':'Private case coverage, not published prematch evidence; no synthetic NO SIGNAL for excluded fixtures.',
    }


def main(argv=None) -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases',type=Path,required=True)
    ap.add_argument('--plan-only',action='store_true')
    ap.add_argument('--project-root',type=Path,default=Path.home()/'Projects/football_market_analytics_v2_2')
    ap.add_argument('--science-root',type=Path)
    ap.add_argument('--data-root',type=Path)
    ap.add_argument('--model-python',type=Path,default=Path(os.environ.get('FMA_PORTFOLIO_MODEL_PYTHON') or sys.executable))
    ap.add_argument('--reference-root',type=Path,action='append',default=[])
    ap.add_argument('--checkpoint-dir',type=Path)
    ap.add_argument('--eligible-cases-file',type=Path)
    ap.add_argument('--coverage-file',type=Path)
    ap.add_argument('--baseline-file',type=Path)
    ap.add_argument('--max-case-seconds',type=int,default=120)
    args=ap.parse_args(argv)
    try:
        if not 1<=args.max_case_seconds<=1200:
            raise ParityError('Invalid per-case timeout')
        original=load_cases(private_path(args.cases, ROOT, should_exist=True))
        policy=load_policy()
        eligible,excluded,unverified=plan(original,policy)
        print('ELIGIBILITY PLAN: '+f'{len(original)} total; {len(eligible)} eligible; '+
              f'{len(excluded)} ineligible; {len(unverified)} unverified',flush=True)
        for entry in excluded:
            print(f'CASE {entry["index"]}: INELIGIBLE ({entry["reason"]}); model not invoked',flush=True)
        for entry in unverified:
            print(f'CASE {entry["index"]}: UNVERIFIED ({entry["reason"]}); model not invoked',flush=True)
        if args.plan_only:
            print('PLAN ONLY: no model calls, checkpoints or evidence files changed.')
            return 0
        if unverified:
            raise ParityError('Unknown fixture eligibility: cannot promote incomplete evidence')
        if not eligible:
            raise ParityError('No eligible cases')
        if not all((args.science_root,args.data_root,args.checkpoint_dir,args.eligible_cases_file,
                    args.coverage_file,args.baseline_file)):
            raise ParityError('Missing required runtime or output argument')
        paths=[private_path(p,ROOT,should_exist=False) for p in
               (args.eligible_cases_file,args.coverage_file,args.baseline_file)]
        if len({str(p) for p in paths})!=3 or any(p.exists() for p in paths):
            raise ParityError('Output files must be distinct and must not already exist')
        roots=Roots(args.project_root,args.science_root,args.data_root,args.model_python).resolved()
        identity=source_identity(roots,args.reference_root,ROOT)
        checkpoint_dir=make_private_checkpoint_dir(args.checkpoint_dir,ROOT)
        worker=roots.project/'deployment/public_web/web_app/model_worker.py'
        def run_model(request):
            return execute_frozen_worker(request, project=roots.project,science=roots.science,
                   data=roots.data,worker=worker,executable=str(roots.model_python),
                   timeout_seconds=args.max_case_seconds)
        outputs=run_eligible(eligible,identity,checkpoint_dir=checkpoint_dir,
                             repo_root=ROOT,run_model=run_model)
        baseline={'schema':SCHEMA_BASELINE,
                  'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
                  'runtime':identity,'cases':outputs}
        validate_baseline(baseline)
        covered=coverage_doc(original,eligible,excluded,unverified,digest_file(POLICY_PATH))
        safe_write_private_json(paths[0],{'schema':SCHEMA_CASES,'cases':[row for _,row in eligible]},ROOT)
        safe_write_private_json(paths[1],covered,ROOT)
        safe_write_private_json(paths[2],baseline,ROOT)
        print(f'ELIGIBLE BASELINE CREATED: {len(outputs)} real outputs, '+
              f'{len(excluded)} exclusions recorded separately; files remain PRIVATE.',flush=True)
        if identity['reference_coverage']=='NOT_CAPTURED':
            print('REFERENCE COVERAGE: NOT_CAPTURED; this is NOT production acceptance.',flush=True)
        print('This is NOT Linux parity and NOT a prospective forecast record.')
        return 0
    except (EligibilityPolicyError,ParityError,ForecastUnavailable,OSError,RuntimeError,TypeError,ValueError):
        print('STOPPED: coverage, runtime or private-evidence validation failed. Existing checkpoints retained.',file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('STOPPED: interrupted; eligible checkpoints retained.',file=sys.stderr)
        return 130

if __name__=='__main__':
    raise SystemExit(main())
