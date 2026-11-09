"""Fail-closed, owner-Mac-only bridge to the EXISTING P7.2 scientific worker.

No model or reference files are packaged in this repository. Never enable on
cloud/public hosts. Launcher must bind Streamlit exclusively to 127.0.0.1.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from .forecast_contract import validate_request
from fma_portfolio.eligibility import classify_fixture


class ForecastUnavailable(RuntimeError):
    """The real frozen scientific engine is not available on this host."""


class ForecastIneligible(ForecastUnavailable):
    """Requested fixture is outside frozen coverage; not a NO SIGNAL."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__('Fixture is outside validated model coverage')


def owner_local_enabled() -> bool:
    if os.environ.get('FMA_PORTFOLIO_OWNER_LOCAL') != '1':
        return False
    # Fail closed on Streamlit Cloud or an address accessible over the LAN.
    try:
        from streamlit import config
        return config.get_option('server.address') == '127.0.0.1'
    except (ImportError, AttributeError, RuntimeError, ValueError):
        return False


def _roots() -> tuple[Path, Path, Path, Path]:
    paths = []
    for name in ('FMA_WEB_PROJECT_ROOT', 'FMA_SCIENCE_ROOT', 'FMA_DATA_ROOT'):
        value = os.environ.get(name, '').strip()
        if not value:
            raise ForecastUnavailable('Owner-local frozen runtime roots are not configured')
        try:
            paths.append(Path(value).expanduser().resolve(strict=True))
        except (OSError, RuntimeError) as exc:
            raise ForecastUnavailable('Owner-local runtime directory does not exist') from exc
    project, science, data = paths
    worker = project / 'deployment' / 'public_web' / 'web_app' / 'model_worker.py'
    checks = (worker,
              project / 'backend' / 'public_factory.py',
              project / 'core' / 'scientific_bridge.py',
              science / 'prematch_analysis' / 'prematch_analysis_v1' / 'run_prematch_analysis_v1.py',
              data / 'p1_context' / 'p1_prematch_runner_v1' / 'p1_prematch_adapter.py',
              data / 'p2_context' / 'p2_prematch_runner_v1' / 'run_p2_prematch_v1.py')
    if not all(path.is_file() for path in checks):
        raise ForecastUnavailable('The original local scientific runtime is incomplete')
    return project, science, data, worker


def _child_env(parent: dict, sandbox: Path, science: Path, data: Path) -> dict:
    child = {key: parent[key] for key in ('HOME', 'PATH', 'LANG', 'LC_ALL', 'TMPDIR',
                                          'SYSTEMROOT', 'WINDIR', 'SSL_CERT_FILE') if parent.get(key)}
    child.update({
        'FMA_PUBLIC_MODE': '1', 'FMA_STORAGE_BACKEND': 'local',
        'FMA_PUBLIC_SANDBOX_ROOT': str(sandbox),
        'FMA_RUNTIME_ROOT': str(sandbox / 'prematch_artifacts'),
        'FMA_STORAGE_ROOT': str(sandbox / 'app_storage'),
        'FMA_SCIENCE_ROOT': str(science), 'FMA_DATA_ROOT': str(data),
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
    })
    return child


def _clean_projection(raw: object) -> dict:
    if not isinstance(raw, dict) or set(raw) != {'ah', 'ou'}:
        raise ForecastUnavailable('Invalid P7 forecast response')
    result = {}
    for market, choices in (('ah', {'HOME', 'AWAY'}), ('ou', {'OVER', 'UNDER'})):
        item = raw[market]
        if not isinstance(item, dict) or set(item) != {'status', 'direction', 'stake_u'}:
            raise ForecastUnavailable('Invalid P7 market projection')
        status, direction, stake = item['status'], item['direction'], item['stake_u']
        if status == 'FORECAST' and direction in choices and type(stake) in (float, int) and stake == 1.0:
            result[market] = {'status': status, 'direction': direction, 'stake_u': 1.0}
        elif status in ('NO_SIGNAL', 'UNAVAILABLE') and direction is None and stake is None:
            result[market] = {'status': status, 'direction': None, 'stake_u': None}
        else:
            raise ForecastUnavailable('Unknown or unsafe P7 model output')
    return result


def execute_frozen_worker(request: dict, *, project: Path, science: Path, data: Path,
                          worker: Path, timeout_seconds: int = 1050,
                          executable: str | None = None) -> dict:
    """Explicit-roots isolated worker used by local UI and loopback gateway.

    This function does NOT expose an HTTP port and never returns raw worker logs.
    """
    validated = validate_request(request)
    if not 1 <= timeout_seconds <= 1200:
        raise ValueError('Invalid model timeout')
    binary = executable or os.environ.get('FMA_PORTFOLIO_MODEL_PYTHON', '') or sys.executable
    python = Path(binary).expanduser()
    if not python.is_absolute() or not python.is_file():
        raise ForecastUnavailable('The scientific Python interpreter is unavailable')
    with tempfile.TemporaryDirectory(prefix='fma_portfolio_owner_') as tmp:
        sandbox = Path(tmp).resolve()
        for name in ('prematch_artifacts', 'app_storage'):
            (sandbox / name).mkdir(mode=0o700)
        env = _child_env(os.environ, sandbox, science, data)
        try:
            completed = subprocess.run(
                [str(python), '-I', str(worker), str(project)],
                input=json.dumps(validated, allow_nan=False), text=True, capture_output=True,
                cwd=str(sandbox), env=env, timeout=timeout_seconds, check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise ForecastUnavailable('The scientific executor did not complete') from exc
        if len(completed.stdout) > 20480:
            raise ForecastUnavailable('Invalid P7 response size')
        try:
            response = json.loads(completed.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError, TypeError) as exc:
            raise ForecastUnavailable('The scientific executor did not return a forecast') from exc
        if completed.returncode != 0 or not isinstance(response, dict) or response.get('ok') is not True:
            raise ForecastUnavailable('The frozen model could not complete this request')
        return _clean_projection(response.get('result'))


def predict(request: dict, *, timeout_seconds: int = 1050) -> dict:
    """Existing owner-only forecast API; public/cloud access still fails closed."""
    validated = validate_request(request)
    if not owner_local_enabled():
        raise ForecastUnavailable('Real forecasts are disabled outside owner-local loopback mode')
    decision = classify_fixture(validated['league'], validated['home'], validated['away'], validated['fixture_date'])
    if decision.status != 'ELIGIBLE':
        raise ForecastIneligible(decision.reason)
    project, science, data, worker = _roots()
    return execute_frozen_worker(validated, project=project, science=science,
                                 data=data, worker=worker, timeout_seconds=timeout_seconds)
