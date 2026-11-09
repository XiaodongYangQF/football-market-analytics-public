"""Private-only Mac/Linux P7 runtime provenance and deterministic forecast parity.

This module may be published, but all generated baselines, input corpora and
scientific source files MUST stay outside the public repository. It neither
copies nor transfers private scientific files.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
from typing import Callable

from .p7.forecast_contract import validate_request
from .p7.owner_local import _clean_projection

SCHEMA_CASES = 'FMA_PRIVATE_RUNTIME_PARITY_CASES_V1'
SCHEMA_BASELINE = 'FMA_PRIVATE_RUNTIME_PARITY_BASELINE_V1'
SCHEMA_REPORT = 'FMA_PRIVATE_RUNTIME_PARITY_REPORT_V1'
MAX_CASE_BYTES = 300_000
MAX_BASELINE_BYTES = 1_000_000
MAX_CASES = 96
MAX_FILES = 3000
MAX_SOURCE_BYTES = 40_000_000
SOURCE_SUBDIRS = (
    ('project', 'backend'), ('project', 'core'), ('project', 'config'),
    ('project', 'deployment/public_web/web_app'),
    ('science', 'prematch_analysis/prematch_analysis_v1'),
    ('data', 'p1_context/p1_prematch_runner_v1'),
    ('data', 'p2_context/p2_prematch_runner_v1'),
)
REQUIRED_SOURCE = (
    'project/deployment/public_web/web_app/model_worker.py',
    'project/deployment/public_web/web_app/forecast_contract.py',
    'project/backend/public_factory.py',
    'project/backend/public_runtime.py',
    'project/backend/public_weight_policy.py',
    'project/core/scientific_bridge.py',
    'project/core/models.py',
    'project/config/settings.py',
    'science/prematch_analysis/prematch_analysis_v1/run_prematch_analysis_v1.py',
    'data/p1_context/p1_prematch_runner_v1/p1_prematch_adapter.py',
    'data/p2_context/p2_prematch_runner_v1/run_p2_prematch_v1.py',
)
EXCLUDE_PARTS = {'__pycache__', '.git', '.venv', 'venv', 'backups', 'backup',
                 'artifacts', 'outputs'}
CASE_ID_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,47}$')
SHA_RE = re.compile(r'^[a-f0-9]{64}$')
PACKAGE_NAMES = ('numpy', 'pandas', 'scipy', 'scikit-learn', 'statsmodels',
                 'pyarrow', 'pydantic', 'matplotlib', 'streamlit')

class ParityError(ValueError):
    pass


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(',', ':')).encode('utf-8')


def digest_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def digest_file(path: Path, *, max_bytes: int = MAX_SOURCE_BYTES) -> str:
    if not path.is_file() or path.is_symlink():
        raise ParityError('Missing or linked runtime component')
    if path.stat().st_size > max_bytes:
        raise ParityError('Runtime component exceeds audit size cap')
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def private_path(path: Path, public_root: Path, *, should_exist: bool) -> Path:
    """Refuse to write/read sensitive parity data anywhere inside public GitHub."""
    repo = public_root.expanduser().resolve(strict=True)
    target = path.expanduser().resolve(strict=should_exist)
    if target == repo or repo in target.parents:
        raise ParityError('Private evidence path must be OUTSIDE the public GitHub repository')
    if target.is_symlink():
        raise ParityError('Symlinks are not permitted for private evidence')
    if should_exist and not target.is_file():
        raise ParityError('Private evidence file does not exist')
    return target


def read_json(path: Path, max_bytes: int) -> object:
    if path.stat().st_size > max_bytes:
        raise ParityError('Private evidence exceeds size cap')
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError) as exc:
        raise ParityError('Unable to read private JSON evidence') from exc


def load_cases(path: Path) -> list[dict]:
    payload = read_json(path, MAX_CASE_BYTES)
    if not isinstance(payload, dict) or set(payload) != {'schema', 'cases'} or payload['schema'] != SCHEMA_CASES:
        raise ParityError('Invalid private case corpus schema')
    rows = payload['cases']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_CASES:
        raise ParityError('Case corpus must contain between 1 and 96 cases')
    result, seen_id, seen_req = [], set(), set()
    from .hosted_gateway import REQUEST_FIELDS
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'id', 'request'}:
            raise ParityError('Invalid case fields')
        name = row['id']
        if not isinstance(name, str) or not CASE_ID_RE.fullmatch(name) or name in seen_id:
            raise ParityError('Invalid or duplicate case id')
        if not isinstance(row['request'], dict) or set(row['request']) != REQUEST_FIELDS:
            raise ParityError('Case request must contain the exact 12 model inputs')
        try:
            request = validate_request(row['request'])
        except (ValueError, TypeError) as exc:
            raise ParityError('Invalid model input in private corpus') from exc
        signature = digest_bytes(canonical(request))
        if signature in seen_req:
            raise ParityError('Duplicate model input in private corpus')
        seen_id.add(name); seen_req.add(signature)
        result.append({'id': name, 'request': request})
    return result


@dataclass(frozen=True)
class Roots:
    project: Path
    science: Path
    data: Path
    model_python: Path

    def resolved(self) -> 'Roots':
        values = []
        for value in (self.project, self.science, self.data):
            try:
                p = Path(value).expanduser().resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise ParityError('Scientific runtime root not found') from exc
            if not p.is_dir():
                raise ParityError('Scientific runtime root must be a directory')
            values.append(p)
        p = Path(self.model_python).expanduser()
        if not p.is_absolute() or not p.is_file():
            raise ParityError('Model Python must be an existing absolute interpreter path')
        return Roots(*values, p.resolve(strict=True))


def source_manifest(roots: Roots) -> dict[str, str]:
    """Hash model-relevant Python files; paths are relative to logical roots."""
    roots = roots.resolved()
    locations = {'project': roots.project, 'science': roots.science, 'data': roots.data}
    entries: dict[str, str] = {}
    for logical, name in SOURCE_SUBDIRS:
        base = locations[logical] / name
        if not base.is_dir() or base.is_symlink():
            raise ParityError('Required scientific source subtree missing or linked')
        for item in sorted(base.rglob('*.py')):
            relative = item.relative_to(locations[logical])
            if any(part in EXCLUDE_PARTS or part.startswith('.') for part in relative.parts):
                continue
            if item.is_symlink():
                raise ParityError('Scientific Python source must not be symlinked')
            label = logical + '/' + relative.as_posix()
            if label in entries or len(entries) >= MAX_FILES:
                raise ParityError('Scientific source manifest exceeds bounds')
            entries[label] = digest_file(item)
    for name in REQUIRED_SOURCE:
        if name not in entries:
            raise ParityError('Required scientific component missing from source manifest')
    return dict(sorted(entries.items()))


def reference_manifest(reference_roots: list[Path], public_root: Path) -> dict[str, str]:
    """Optional full-tree hash of specifically chosen READ-ONLY reference bundles.

    No raw content is stored, and no directory is automatically copied or shipped.
    Empty reference roots are not accepted to avoid false reassurance.
    """
    entries: dict[str, str] = {}
    suffixes = {'.csv', '.json', '.parquet', '.feather', '.npy', '.npz',
                '.pkl', '.pickle', '.joblib', '.xlsx', '.txt', '.yaml', '.yml'}
    for index, untrusted in enumerate(reference_roots):
        value = untrusted.expanduser()
        if value.is_symlink():
            raise ParityError('Reference root must not be symlinked')
        root = value.resolve(strict=True)
        if not root.is_dir():
            raise ParityError('Reference root must be a directory')
        if root == public_root or public_root in root.parents:
            raise ParityError('Private reference files must not be in public GitHub')
        found = 0
        for file in sorted(root.rglob('*')):
            if not file.is_file() or file.suffix.lower() not in suffixes:
                continue
            if any(part.startswith('.') or part in EXCLUDE_PARTS for part in file.relative_to(root).parts):
                continue
            if file.is_symlink():
                raise ParityError('Reference manifest includes a symlink')
            key = f'reference_{index}/' + file.relative_to(root).as_posix()
            if len(entries) >= MAX_FILES:
                raise ParityError('Reference manifest exceeds file limit')
            entries[key] = digest_file(file, max_bytes=2_000_000_000)
            found += 1
        if not found:
            raise ParityError('Reference root has no supported data files')
    return dict(sorted(entries.items()))


def interpreter_report(executable: Path) -> dict:
    """Whitelisted Python/package versions, NO arbitrary pip freeze or secrets."""
    code = '''import importlib.metadata as m, json, platform, sys
names = ['numpy','pandas','scipy','scikit-learn','statsmodels','pyarrow','pydantic','matplotlib','streamlit']
pkgs = {}
for n in names:
    try: pkgs[n] = m.version(n)
    except m.PackageNotFoundError: pkgs[n] = None
print(json.dumps({'python':platform.python_version(), 'platform':platform.system(), 'machine':platform.machine(),'packages':pkgs}))'''
    try:
        proc = subprocess.run([str(executable), '-I', '-c', code],
                              capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0 or len(proc.stdout) > 5000:
            raise ParityError('Scientific interpreter metadata probe failed')
        value = json.loads(proc.stdout)
        if not isinstance(value, dict) or set(value) != {'python', 'platform', 'machine', 'packages'}:
            raise ParityError('Invalid interpreter version probe')
        return value
    except (OSError, subprocess.TimeoutExpired, ValueError, UnicodeError) as exc:
        raise ParityError('Unable to inspect scientific Python interpreter') from exc


def source_identity(roots: Roots, reference_roots: list[Path], public_root: Path) -> dict:
    sources = source_manifest(roots)
    references = reference_manifest(reference_roots, public_root)
    env = interpreter_report(roots.model_python)
    return {
        'source_files': sources, 'source_sha256': digest_bytes(canonical(sources)),
        'reference_files': references, 'reference_sha256': digest_bytes(canonical(references)),
        'reference_coverage': 'DECLARED_ROOTS_ONLY' if references else 'NOT_CAPTURED',
        'interpreter': env,
    }


def _case_result(row: dict, run_model: Callable[[dict], dict]) -> dict:
    begin = time.perf_counter()
    projection = _clean_projection(run_model(row['request']))
    elapsed = time.perf_counter() - begin
    return {'id': row['id'],
            'request_sha256': digest_bytes(canonical(row['request'])),
            'result': projection, 'wall_seconds': round(elapsed, 4)}


def make_baseline(cases: list[dict], identity: dict,
                  run_model: Callable[[dict], dict]) -> dict:
    rows = [_case_result(row, run_model) for row in cases]
    return {'schema': SCHEMA_BASELINE,
            'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
            'runtime': identity, 'cases': rows}


def validate_baseline(baseline: object) -> dict:
    if not isinstance(baseline, dict) or set(baseline) != {'schema', 'created_at_utc', 'runtime', 'cases'}:
        raise ParityError('Invalid baseline schema')
    if baseline['schema'] != SCHEMA_BASELINE:
        raise ParityError('Unsupported baseline version')
    runtime = baseline['runtime']
    if not isinstance(runtime, dict) or set(runtime) != {'source_files', 'source_sha256',
             'reference_files', 'reference_sha256', 'reference_coverage', 'interpreter'}:
        raise ParityError('Invalid runtime provenance')
    for name in ('source_files', 'reference_files'):
        value = runtime[name]
        if not isinstance(value, dict) or len(value) > MAX_FILES or any(
                not isinstance(k, str) or not isinstance(v, str) or not SHA_RE.fullmatch(v)
                for k, v in value.items()):
            raise ParityError('Invalid source/reference file digests')
    if (runtime['source_sha256'] != digest_bytes(canonical(runtime['source_files'])) or
        runtime['reference_sha256'] != digest_bytes(canonical(runtime['reference_files']))):
        raise ParityError('Invalid runtime manifest hash')
    if not isinstance(baseline['cases'], list) or not 1 <= len(baseline['cases']) <= MAX_CASES:
        raise ParityError('Invalid baseline case count')
    seen = set()
    for row in baseline['cases']:
        if not isinstance(row, dict) or set(row) != {'id', 'request_sha256', 'result', 'wall_seconds'}:
            raise ParityError('Invalid baseline row')
        if not isinstance(row['id'], str) or not CASE_ID_RE.fullmatch(row['id']) or row['id'] in seen:
            raise ParityError('Invalid or repeated baseline case ID')
        if not isinstance(row['request_sha256'], str) or not SHA_RE.fullmatch(row['request_sha256']):
            raise ParityError('Invalid baseline request hash')
        _clean_projection(row['result'])
        if (type(row['wall_seconds']) not in (int,float) or
            not 0 <= row['wall_seconds'] < 1_000_000):
            raise ParityError('Invalid baseline run time')
        seen.add(row['id'])
    return baseline


def compare_baseline(baseline: dict, cases: list[dict], identity: dict,
                     run_model: Callable[[dict], dict], *, min_cases: int = 20,
                     max_case_seconds: float = 1200.) -> dict:
    """Fail closed on missing/extra cases, source drift, reference drift and predictions."""
    validate_baseline(baseline)
    old = {r['id']: r for r in baseline['cases']}
    new = {r['id']: r for r in cases}
    if old.keys() != new.keys():
        raise ParityError('Baseline and verifier case IDs differ')
    for name, row in new.items():
        if old[name]['request_sha256'] != digest_bytes(canonical(row['request'])):
            raise ParityError('Baseline inputs differ from current input corpus')
    identity_checks = {
        'scientific_source': identity['source_sha256'] == baseline['runtime']['source_sha256'],
        'declared_reference_data': identity['reference_sha256'] == baseline['runtime']['reference_sha256'],
        'reference_coverage': identity['reference_coverage'] == baseline['runtime']['reference_coverage'],
    }
    runs = []
    for row in cases:
        actual = _case_result(row, run_model)
        expected = old[row['id']]
        runs.append({'id': row['id'],
                     'input_match': True,
                     'projection_match': actual['result'] == expected['result'],
                     'wall_seconds': actual['wall_seconds'],
                     'within_wall_budget': actual['wall_seconds'] <= max_case_seconds})
    elapsed = [r['wall_seconds'] for r in runs]
    count = len(runs)
    statuses = {(market, row['result'][market]['status'])
                for row in baseline['cases'] for market in ('ah','ou')}
    league_coverage = len({row['request']['league'] for row in cases})
    passes_coverage = (count >= min_cases and league_coverage >= 3 and
                       all(('ah', value) in statuses for value in ('FORECAST', 'NO_SIGNAL')) and
                       all(('ou', value) in statuses for value in ('FORECAST', 'NO_SIGNAL')))
    old_env = baseline['runtime']['interpreter']
    new_env = identity['interpreter']
    package_match = (old_env['python'] == new_env['python'] and
                     old_env['packages'] == new_env['packages'])
    mac_linux = old_env['platform'] == 'Darwin' and new_env['platform'] == 'Linux'
    all_equal = all(identity_checks.values()) and all(r['projection_match'] and r['within_wall_budget'] for r in runs)
    return {'schema': SCHEMA_REPORT,
            'case_count': count,
            'identity_checks': identity_checks,
            'output_matches': sum(r['projection_match'] for r in runs),
            'case_budget_matches': sum(r['within_wall_budget'] for r in runs),
            'coverage_gate': passes_coverage,
            'league_coverage': league_coverage,
            'cross_platform_mac_linux': mac_linux,
            'scientific_dependency_versions_equal': package_match,
            'p50_wall_seconds': round(statistics.median(elapsed), 3),
            'max_wall_seconds': round(max(elapsed), 3),
            'per_case': runs,
            'parity_pass': all_equal,
            'promotion_candidate': (all_equal and passes_coverage and mac_linux and package_match
                                    and identity['reference_coverage'] != 'NOT_CAPTURED'),
            'note': 'Mac/Linux production equivalence requires real cross-host execution, not a local mock.',
    }


def safe_write_private_json(target: Path, payload: object, repo: Path) -> None:
    output = private_path(target, repo, should_exist=False)
    if output.exists():
        raise ParityError('Existing private evidence cannot be overwritten')
    if not output.parent.is_dir():
        raise ParityError('Private evidence directory must exist first')
    text = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if len(text.encode('utf-8')) > MAX_BASELINE_BYTES:
        raise ParityError('Private evidence too large')
    fd = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
