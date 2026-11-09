#!/usr/bin/env python3
"""Manually exercise the loopback-hosted contract using a local private JSON input.

This script never publishes data to GitHub or writes a portfolio forecast.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fma_portfolio.hosted_client import predict_hosted
from fma_portfolio.p7.owner_local import ForecastUnavailable
from fma_portfolio.p7.forecast_contract import InvalidForecastInput


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True,help='A private JSON file containing exact P7 request fields')
    args=parser.parse_args(argv)
    try:
        if args.request.resolve().is_relative_to(ROOT):
            raise ValueError('Keep model request files OUTSIDE the public repository')
        data=json.loads(args.request.read_text(encoding='utf-8'))
        projection=predict_hosted(data)
    except (ValueError,OSError,InvalidForecastInput,ForecastUnavailable) as exc:
        print(f'PILOT CHECK STOPPED: {type(exc).__name__}',file=sys.stderr)
        return 2
    print(json.dumps({'ok':True,'result':projection},indent=2))
    print('Pilot transport verified. This is not independent model parity or a public deployment.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
