#!/usr/bin/env python3
"""P8.1C-2: preflight, capture a real Mac baseline, then check Linux parity.

Never commits/uploads Private cases, model code, or parity baseline to GitHub.
This CLI executes the EXISTING frozen P7 worker; no synthetic model results.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fma_portfolio.runtime_parity import (Roots, ParityError, load_cases, private_path,
    source_identity, make_baseline, validate_baseline, compare_baseline,
    read_json, safe_write_private_json, MAX_BASELINE_BYTES, digest_file)
from fma_portfolio.eligibility import POLICY_PATH
from fma_portfolio.p7.owner_local import execute_frozen_worker, ForecastUnavailable


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preflight','baseline','verify'))
    parser.add_argument('--project-root',type=Path,default=Path.home()/'Projects/football_market_analytics_v2_2')
    parser.add_argument('--science-root',type=Path,required=True)
    parser.add_argument('--data-root',type=Path,required=True)
    parser.add_argument('--model-python',type=Path,default=Path(os.environ.get('FMA_PORTFOLIO_MODEL_PYTHON') or sys.executable))
    parser.add_argument('--reference-root',type=Path,action='append',default=[])
    parser.add_argument('--cases',type=Path)
    parser.add_argument('--baseline-file',type=Path)
    parser.add_argument('--report-file',type=Path)
    parser.add_argument('--eligibility-coverage-file',type=Path,
                        help='Private exclusion ledger from eligible_mac_baseline.py')
    parser.add_argument('--max-case-seconds',type=float,default=1200.)
    parser.add_argument('--min-cases',type=int,default=20)
    args=parser.parse_args(argv)
    try:
        if not 1 <= args.max_case_seconds <= 1200 or not 1 <= args.min_cases <= 96:
            raise ParityError('Invalid run budget or minimum cases')
        roots=Roots(args.project_root,args.science_root,args.data_root,args.model_python).resolved()
        identity=source_identity(roots,args.reference_root,ROOT)
        print('SOURCE INVENTORY PASS:',len(identity['source_files']), 'Python files')
        print('SOURCE SHA256:',identity['source_sha256'])
        print('REFERENCE COVERAGE:',identity['reference_coverage'],
              f"({len(identity['reference_files'])} hashed files)")
        print('INTERPRETER:',identity['interpreter']['platform'],
              identity['interpreter']['python'],identity['interpreter']['machine'])
        if args.mode == 'preflight':
            print('PREFLIGHT PASS: paths, critical source files and interpreter found; NO MODEL RUN performed.')
            print('Reference inventory only covers explicitly declared --reference-root paths.')
            return 0
        if args.cases is None or args.baseline_file is None:
            raise ParityError('Provide --cases and --baseline-file for baseline or verify')
        case_path=private_path(args.cases,ROOT,should_exist=True)
        baseline_path=private_path(args.baseline_file,ROOT,should_exist=args.mode=='verify')
        rows=load_cases(case_path)
        worker=roots.project/'deployment/public_web/web_app/model_worker.py'
        def executor(request:dict) -> dict:
            return execute_frozen_worker(request,project=roots.project,science=roots.science,
                data=roots.data,worker=worker,executable=str(roots.model_python),
                timeout_seconds=int(args.max_case_seconds))
        if args.mode == 'baseline':
            if identity['reference_coverage']=='NOT_CAPTURED':
                print('WARNING: reference files were NOT inventoried; baseline not sufficient for production promotion.')
            baseline=make_baseline(rows,identity,executor)
            safe_write_private_json(baseline_path,baseline,ROOT)
            print(f'BASELINE CREATED: {len(rows)} real frozen-worker calls; evidence written privately.')
            print('This Mac-only baseline is NOT evidence of Linux parity.')
            return 0
        coverage_ok = False
        if args.eligibility_coverage_file is not None:
            coverage_path = private_path(args.eligibility_coverage_file,ROOT,should_exist=True)
            cover = read_json(coverage_path,MAX_BASELINE_BYTES)
            if (not isinstance(cover,dict) or
                cover.get('schema') != 'FMA_PRIVATE_ELIGIBILITY_COVERAGE_V1' or
                cover.get('policy_sha256') != digest_file(POLICY_PATH) or
                cover.get('eligible_count') != len(rows) or
                cover.get('unverified_count') != 0 or
                cover.get('original_case_count') != cover.get('eligible_count',-1) + cover.get('excluded_count',-1)):
                raise ParityError('Eligibility evidence does not match frozen public policy or cases')
            coverage_ok = True
        baseline=validate_baseline(read_json(baseline_path,MAX_BASELINE_BYTES))
        report=compare_baseline(baseline,rows,identity,executor,
                  min_cases=args.min_cases,max_case_seconds=args.max_case_seconds)
        if args.report_file is not None:
            safe_write_private_json(args.report_file,report,ROOT)
        print('REAL ENGINE COMPARISON:',report['output_matches'],'/',report['case_count'],'exact AH/OU matches')
        print('SOURCE / REFERENCES:',report['identity_checks'])
        print('WALL TIME: median',report['p50_wall_seconds'],'s / maximum',report['max_wall_seconds'],'s')
        print('COVERAGE GATE:', 'PASS' if report['coverage_gate'] else 'INCOMPLETE',
              f"({report['league_coverage']} leagues)")
        print('MAC→LINUX PLATFORM:', 'CONFIRMED' if report['cross_platform_mac_linux'] else 'NOT CONFIRMED')
        print('PYTHON/PACKAGE VERSIONS:', 'EXACT' if report['scientific_dependency_versions_equal'] else 'DRIFT')
        print('PARITY:', 'PASS' if report['parity_pass'] else 'FAIL')
        print('ELIGIBILITY POLICY EVIDENCE:', 'VERIFIED' if coverage_ok else 'NOT PROVIDED')
        print('PROMOTION-CANDIDATE GATE:', 'PASS' if report['promotion_candidate'] and coverage_ok else 'NOT READY')
        if identity['interpreter']['platform'] != 'Linux':
            print('NOTE: This run was NOT on Linux; cross-platform parity remains unverified.')
        if not report['parity_pass']:
            return 1
        return 0
    except (ParityError, ForecastUnavailable, OSError, RuntimeError, TypeError, ValueError) as exc:
        # Avoid revealing sensitive absolute paths / internal model diagnostics in public logs.
        print('STOPPED: scientific runtime or private evidence check failed. Review private configuration locally.',file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
