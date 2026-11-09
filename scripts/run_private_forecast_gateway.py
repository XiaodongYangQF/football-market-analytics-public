#!/usr/bin/env python3
"""Run authenticated, quota-limited frozen P7 model gateway on 127.0.0.1 ONLY.

Private-science roots and secret token stay on the owner's machine. Never
publish this port directly to the Internet or run it within a public GitHub job.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from fma_portfolio.hosted_gateway import GatewayState, LoopbackGateway
from fma_portfolio.p7.owner_local import execute_frozen_worker
from scripts.run_owner_local import _safe_root, _read_original_roots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,default=Path.home()/'Projects/football_market_analytics_v2_2')
    parser.add_argument('--science-root')
    parser.add_argument('--data-root')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--max-per-hour',type=int,default=4)
    parser.add_argument('--cooldown-seconds',type=float,default=30.)
    parser.add_argument('--model-timeout-seconds',type=int,default=1050)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args(argv)
    try:
        project = _safe_root(str(args.project_root))
        roots = _read_original_roots(project)
        science = _safe_root(args.science_root or os.environ.get('FMA_SCIENCE_ROOT') or roots.get('FMA_SCIENCE_ROOT',''))
        data = _safe_root(args.data_root or os.environ.get('FMA_DATA_ROOT') or roots.get('FMA_DATA_ROOT',''))
        worker = project/'deployment/public_web/web_app/model_worker.py'
        checks=(worker, project/'backend/public_factory.py', project/'core/scientific_bridge.py',
                science/'prematch_analysis/prematch_analysis_v1/run_prematch_analysis_v1.py',
                data/'p1_context/p1_prematch_runner_v1/p1_prematch_adapter.py',
                data/'p2_context/p2_prematch_runner_v1/run_p2_prematch_v1.py')
        if not all(path.is_file() for path in checks):
            raise ValueError('Frozen worker and scientific runtime are incomplete')
        if not 1 <= args.model_timeout_seconds <= 1200:
            raise ValueError('Invalid timeout')
        if not 1 <= args.port <= 65535:
            raise ValueError('Invalid port')
        executable=os.environ.get('FMA_PORTFOLIO_MODEL_PYTHON','') or sys.executable
        if not Path(executable).is_absolute() or not Path(executable).is_file():
            raise ValueError('Scientific Python interpreter unavailable')
        if args.check:
            print('GATEWAY PREFLIGHT PASS: frozen worker, model roots and interpreter found.')
            print('No HTTP service opened and no real model run performed.')
            return 0
        token=os.environ.get('FMA_GATEWAY_TOKEN','')
        if not token:
            raise ValueError('Missing FMA_GATEWAY_TOKEN (never put it in GitHub or command history)')
        def executor(request:dict) -> dict:
            return execute_frozen_worker(request,project=project,science=science,data=data,
                                         worker=worker,timeout_seconds=args.model_timeout_seconds,
                                         executable=executable)
        state=GatewayState(token=token,executor=executor,
                           max_per_hour=args.max_per_hour,cooldown_seconds=args.cooldown_seconds)
        with LoopbackGateway(args.port,state) as server:
            print(f'LOOPBACK GATEWAY ACTIVE: http://127.0.0.1:{args.port}/healthz',flush=True)
            print('NOT PUBLIC. A production deployment requires HTTPS, independent access control and infrastructure limits.',flush=True)
            server.serve_forever(poll_interval=0.2)
        return 0
    except (ValueError,OSError,RuntimeError) as exc:
        print(f'STOPPED: {exc}',file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
