#!/usr/bin/env python3
"""Launch Portfolio with real existing P7 model, bound ONLY to loopback on Mac.

Run from owner machine; never invoke in cloud. Reads only the 2 external root
paths from the original project's local .env if they are not provided explicitly.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def _safe_root(value: str) -> Path:
    if not value or any(c in value for c in ('$','`','\x00','\r','\n')):
        raise ValueError('Provide a literal existing directory path')
    root = Path(value).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Runtime root must be a directory')
    return root


def _read_original_roots(project: Path) -> dict[str, str]:
    values = {}
    path = project / '.env'
    if not path.is_file():
        return values
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line.startswith('export '):
            line = line[len('export '):]
        key, sep, value = line.partition('=')
        key = key.strip()
        if sep and key in ('FMA_SCIENCE_ROOT', 'FMA_DATA_ROOT'):
            value = value.strip().strip('"').strip("'")
            if value and not any(c in value for c in ('$','`','\x00')):
                values[key] = value
    return values


def build_owner_env(project: Path, science: Path, data: Path) -> dict[str, str]:
    allowed = ('HOME','PATH','LANG','LC_ALL','TMPDIR','CONDA_PREFIX',
               'CONDA_DEFAULT_ENV','SSL_CERT_FILE','REQUESTS_CA_BUNDLE')
    env = {k: os.environ[k] for k in allowed if os.environ.get(k)}
    env.update({
        'FMA_PORTFOLIO_OWNER_LOCAL':'1',
        'FMA_WEB_PROJECT_ROOT':str(project),
        'FMA_SCIENCE_ROOT':str(science),
        'FMA_DATA_ROOT':str(data),
        'PYTHONDONTWRITEBYTECODE':'1',
    })
    # Optional existing scientific env Python rather than a new portfolio env.
    if os.environ.get('FMA_PORTFOLIO_MODEL_PYTHON'):
        env['FMA_PORTFOLIO_MODEL_PYTHON'] = os.environ['FMA_PORTFOLIO_MODEL_PYTHON']
    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,default=Path.home()/'Projects/football_market_analytics_v2_2')
    parser.add_argument('--science-root')
    parser.add_argument('--data-root')
    parser.add_argument('--port',type=int,default=8504)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args(argv)
    try:
        project=_safe_root(str(args.project_root))
        if not (project/'deployment/public_web/web_app/model_worker.py').is_file():
            raise ValueError('P7.4 owner-local model worker is missing from Private project')
        roots=_read_original_roots(project)
        science=_safe_root(args.science_root or os.environ.get('FMA_SCIENCE_ROOT') or roots.get('FMA_SCIENCE_ROOT',''))
        data=_safe_root(args.data_root or os.environ.get('FMA_DATA_ROOT') or roots.get('FMA_DATA_ROOT',''))
        required=(science/'prematch_analysis/prematch_analysis_v1/run_prematch_analysis_v1.py',
                  data/'p1_context/p1_prematch_runner_v1/p1_prematch_adapter.py',
                  data/'p2_context/p2_prematch_runner_v1/run_p2_prematch_v1.py')
        if not all(x.is_file() for x in required):
            raise ValueError('External frozen scientific scripts are missing')
        if not 1 <= args.port <= 65535:
            raise ValueError('Invalid TCP port')
        if args.check:
            print('OWNER-LOCAL PREFLIGHT PASS: P7 worker and scientific roots found.')
            print('No forecast executed; model parity requires an actual Mac forecast run.')
            return 0
        # Enforce loopback even when someone has a global Streamlit config.
        cmd=[sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),
             '--server.address=127.0.0.1',f'--server.port={args.port}',
             '--server.headless=true','--server.fileWatcherType=none']
        print(f'Owner-local portfolio: http://127.0.0.1:{args.port}',flush=True)
        return subprocess.run(cmd,cwd=str(ROOT),env=build_owner_env(project,science,data),check=False).returncode
    except (ValueError, OSError, RuntimeError) as exc:
        print(f'STOPPED: {exc}',file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
