#!/usr/bin/env python3
"""Compare exact real P7 local model vs separately running gateway on ONE request.

Requires a real frozen model, a running loopback gateway and the same private
scientific configuration. No simulated prediction and no data files committed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from fma_portfolio.p7.owner_local import execute_frozen_worker, ForecastUnavailable
from fma_portfolio.hosted_client import predict_hosted, HostedConfigurationError
from fma_portfolio.p7.forecast_contract import validate_request, InvalidForecastInput
from scripts.run_owner_local import _read_original_roots, _safe_root


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--project-root',type=Path,default=Path.home()/'Projects/football_market_analytics_v2_2')
    parser.add_argument('--science-root')
    parser.add_argument('--data-root')
    args=parser.parse_args(argv)
    try:
        if args.request.resolve().is_relative_to(ROOT):
            raise ValueError('Private request JSON must be outside the public GitHub repository')
        req=validate_request(json.loads(args.request.read_text(encoding='utf-8')))
        project=_safe_root(str(args.project_root))
        old_roots=_read_original_roots(project)
        science=_safe_root(args.science_root or os.environ.get('FMA_SCIENCE_ROOT') or old_roots.get('FMA_SCIENCE_ROOT',''))
        data=_safe_root(args.data_root or os.environ.get('FMA_DATA_ROOT') or old_roots.get('FMA_DATA_ROOT',''))
        worker=project/'deployment/public_web/web_app/model_worker.py'
        if not worker.is_file():raise ValueError('Original model worker unavailable')
        local=execute_frozen_worker(req,project=project,science=science,data=data,worker=worker)
        gateway=predict_hosted(req)
    except (OSError,ValueError,InvalidForecastInput,ForecastUnavailable,HostedConfigurationError) as exc:
        print(f'PARITY STOPPED: {type(exc).__name__}. Review the private environment and model runner.',file=sys.stderr)
        return 2
    if local != gateway:
        print('PARITY FAIL: original local and gateway outputs differ. Hosted deployment must remain disabled.',file=sys.stderr)
        return 1
    print('REAL SCIENTIFIC PARITY PASS: exact AH/OU status, direction and stake match on this case.')
    print('One-case parity is not enough for production; repeat on diverse markets and NO SIGNAL cases.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
