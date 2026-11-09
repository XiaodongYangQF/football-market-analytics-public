from __future__ import annotations
import copy
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import resumable_mac_baseline as rb
from fma_portfolio.runtime_parity import ParityError, Roots, source_identity, REQUIRED_SOURCE
from fma_portfolio.p7.owner_local import ForecastUnavailable

SIGNAL = {'ah': {'status': 'FORECAST', 'direction': 'HOME', 'stake_u': 1.0},
          'ou': {'status': 'NO_SIGNAL', 'direction': None, 'stake_u': None}}
NO = {'ah': {'status': 'NO_SIGNAL', 'direction': None, 'stake_u': None},
      'ou': {'status': 'NO_SIGNAL', 'direction': None, 'stake_u': None}}
BASE_REQ = {
    'league': 'E0', 'home': 'Liverpool', 'away': 'Fulham', 'fixture_date': '2026-11-21',
    'ah_line': -1.0, 'ah_home_odds': 1.93, 'ah_away_odds': 1.95,
    'asian_line': 2.75, 'asian_over_odds': 1.9, 'asian_under_odds': 1.96,
    'fixed_over_odds': 1.82, 'fixed_under_odds': 2.02,
}

def fake_roots(tmp_path: Path) -> Roots:
    roots = Roots(tmp_path/'private_project',tmp_path/'science',tmp_path/'data',Path(sys.executable))
    for key in REQUIRED_SOURCE:
        group, rel = key.split('/', 1)
        file = getattr(roots,group) / rel
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('print("stub")\n')
    return roots

def cases(n=2):
    return [{'id': f'fixture_{i:02d}',
             'request': {**BASE_REQ, 'home': f'Home {i}', 'away': f'Away {i}'}}
            for i in range(n)]


def test_private_resumption_skips_completed_cases_after_failure(tmp_path):
    identity = source_identity(fake_roots(tmp_path), [], ROOT)
    folder = rb.make_private_checkpoint_dir(tmp_path/'checkpoint', ROOT)
    rows = cases(3)
    calls = []
    def fail_on_second(request):
        calls.append(request['home'])
        if request['home'] == rows[1]['request']['home']:
            raise ForecastUnavailable('simulated worker error')
        return SIGNAL
    with pytest.raises(ForecastUnavailable):
        rb.process_cases(rows,identity,checkpoint_dir=folder,repo_root=ROOT,run_model=fail_on_second)
    assert (folder/'case_001.json').is_file()
    assert not (folder/'case_002.json').exists()
    assert len(calls)==2
    calls.clear()
    result = rb.process_cases(rows, identity, checkpoint_dir=folder,
                              repo_root=ROOT, run_model=lambda req: (calls.append(req['home']) or NO))
    assert len(result)==3
    assert len(calls)==2  # first checkpoint reused, never re-runs
    assert result[0]['result']==SIGNAL
    assert result[1]['result']==NO


def test_existing_checkpoint_refuses_changed_identity_and_input(tmp_path):
    identity = source_identity(fake_roots(tmp_path), [], ROOT)
    folder = rb.make_private_checkpoint_dir(tmp_path/'checkpoint', ROOT)
    one = cases(1)
    rb.process_cases(one,identity,checkpoint_dir=folder,repo_root=ROOT,run_model=lambda req:SIGNAL)
    modified=copy.deepcopy(identity)
    modified['source_sha256']='0'*64
    with pytest.raises(ParityError,match='identity changed'):
        rb.process_cases(one,modified,checkpoint_dir=folder,repo_root=ROOT,run_model=lambda req:NO)
    edited=copy.deepcopy(one)
    edited[0]['request']['asian_line']=3.0
    with pytest.raises(ParityError,match='identity changed'):
        rb.process_cases(edited,identity,checkpoint_dir=folder,repo_root=ROOT,run_model=lambda req:NO)


def test_checkpoint_not_allowed_inside_public_and_must_be_private(tmp_path):
    with pytest.raises(ParityError,match='OUTSIDE'):
        rb.make_private_checkpoint_dir(ROOT/'private_new',ROOT)
    folder=tmp_path/'not_private';folder.mkdir(mode=0o755)
    folder.chmod(0o755)
    with pytest.raises(ParityError,match='owner-only'):
        rb.make_private_checkpoint_dir(folder,ROOT)


def test_corrupt_checkpoint_refused(tmp_path):
    identity=source_identity(fake_roots(tmp_path),[],ROOT)
    folder=rb.make_private_checkpoint_dir(tmp_path/'private',ROOT)
    p=folder/'case_001.json';p.write_text('{}');p.chmod(0o600)
    with pytest.raises(ParityError,match='schema mismatch'):
        rb.process_cases(cases(1),identity,checkpoint_dir=folder,repo_root=ROOT,run_model=lambda req:SIGNAL)

def test_cli_single_case_end_to_end_creates_strict_baseline(tmp_path):
    import json
    roots=fake_roots(tmp_path)
    worker=roots.project/'deployment/public_web/web_app/model_worker.py'
    worker.write_text('''import json,sys
json.loads(sys.stdin.read())
print(json.dumps({'ok':True,'result':{'ah':{'status':'FORECAST','direction':'HOME','stake_u':1.0},'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}}}))
''')
    src=tmp_path/'cases.json'
    from fma_portfolio.runtime_parity import SCHEMA_CASES, validate_baseline
    src.write_text(json.dumps({'schema':SCHEMA_CASES,'cases':cases(1)}))
    baseline=tmp_path/'baseline.json'
    checkpoint=tmp_path/'checkpoints'
    cli=['--project-root',str(roots.project),'--science-root',str(roots.science),
         '--data-root',str(roots.data),'--model-python',sys.executable,
         '--cases',str(src),'--baseline-file',str(baseline),
         '--checkpoint-dir',str(checkpoint),'--max-case-seconds','20']
    assert rb.main(cli)==0
    assert baseline.exists()
    assert validate_baseline(json.loads(baseline.read_text()))['cases'][0]['result']==SIGNAL
    assert (checkpoint/'case_001.json').is_file()
    assert rb.main(cli)==2  # will not overwrite baseline on a second run
