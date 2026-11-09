"""P8.1B: P7 form, fail-closed execution, original archive contract integration."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from unittest.mock import patch
import pytest

from fma_portfolio.p7.forecast_contract import InvalidForecastInput, validate_request
from fma_portfolio.p7.saved_forecasts import create_record, archive_json, parse_archive, merge_records
from fma_portfolio.p7.fixtures_store import load_fixtures, fixture_options
from fma_portfolio.p7.owner_local import _clean_projection, _child_env, predict, ForecastUnavailable


REQ = {'league':'E0','home':'Leeds','away':'Tottenham', 'fixture_date':'2026-11-07',
       'ah_line':-0.25,'ah_home_odds':1.95,'ah_away_odds':1.9,
       'asian_line':2.5,'asian_over_odds':1.95,'asian_under_odds':1.9,
       'fixed_over_odds':1.9,'fixed_under_odds':1.95}


def test_exact_three_input_markets():
    assert set(validate_request(REQ)) == set(REQ)
    assert validate_request(REQ)['asian_line'] == 2.5


@pytest.mark.parametrize('key,value', [('ah_line',-0.12),('asian_line',2.6),('ah_home_odds',1.0),
                                       ('fixed_over_odds',float('nan')),('home','Tottenham')])
def test_invalid_inputs_rejected(key,value):
    with pytest.raises(InvalidForecastInput):
        validate_request(dict(REQ,**{key:value}))


def test_unconfigured_public_site_fails_closed(monkeypatch):
    monkeypatch.delenv('FMA_PORTFOLIO_OWNER_LOCAL',raising=False)
    with pytest.raises(ForecastUnavailable):
        predict(REQ)


def test_projection_exact_allowlist():
    x = _clean_projection({'ah':{'status':'FORECAST','direction':'HOME','stake_u':1.0},
                           'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}})
    assert x['ah']['direction']=='HOME' and x['ou']['direction'] is None


@pytest.mark.parametrize('invalid', [
    {'ah':{'status':'FORECAST','direction':'OVER','stake_u':1.0},'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}},
    {'ah':{'status':'FORECAST','direction':'HOME','stake_u':2.0},'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}},
    {'ah':{'status':'FORECAST','direction':'HOME','stake_u':1.0,'secret':'x'},'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}},
    {'ah':{'status':'NO_SIGNAL','direction':'HOME','stake_u':None},'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}},
])
def test_invalid_projection_fails_closed(invalid):
    with pytest.raises(ForecastUnavailable):_clean_projection(invalid)


def test_child_env_does_not_inherit_secrets(tmp_path):
    env=_child_env({'PATH':'/bin', 'PRIVATE_API_KEY':'never', 'FMA_DATABASE_URL':'db-secret'},
                   tmp_path,tmp_path/'science',tmp_path/'data')
    assert 'PRIVATE_API_KEY' not in env and 'FMA_DATABASE_URL' not in env
    assert env['FMA_PUBLIC_MODE']=='1'


def test_model_subprocess_protocol_still_uses_genuine_worker(tmp_path,monkeypatch):
    worker=tmp_path/'model_worker.py';worker.write_text('# placeholder')
    monkeypatch.setattr('fma_portfolio.p7.owner_local.owner_local_enabled',lambda:True)
    monkeypatch.setattr('fma_portfolio.p7.owner_local._roots',lambda:(tmp_path,tmp_path,tmp_path,worker))
    returned={'ah':{'status':'FORECAST','direction':'AWAY','stake_u':1.0},
              'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}}
    def fake_run(command, **kwargs):
        assert command[1]=='-I' and str(worker)==command[2]
        assert json.loads(kwargs['input'])['ah_line']==REQ['ah_line']
        assert kwargs['env']['FMA_RUNTIME_ROOT'].startswith(kwargs['cwd'])
        return subprocess.CompletedProcess(command,0,json.dumps({'ok':True,'result':returned}),'')
    monkeypatch.setattr('fma_portfolio.p7.owner_local.subprocess.run',fake_run)
    result=predict(REQ,timeout_seconds=5)
    assert result==returned


def test_saved_forecast_uses_original_p7_4_schema():
    response={'ah':{'status':'FORECAST','direction':'AWAY','stake_u':1.0},
              'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}}
    r=create_record(REQ,response,competition='Premier League',display_home='Leeds',display_away='Tottenham',
                   now=datetime(2026,11,7,tzinfo=timezone.utc))
    assert r['policy_version'].startswith('PUBLIC_V2')
    data=archive_json([r]);restored=parse_archive(data)
    assert restored==[r]
    assert merge_records(restored,restored)[1]==0


def test_public_fixtures_are_opt_in():
    assert load_fixtures(Path(__file__).resolve().parents[1]/'data/fixtures.csv','E0') == []


def test_no_private_model_sources_bundled():
    root=Path(__file__).resolve().parents[1]
    assert not (root/'core').exists() and not (root/'backend').exists()
    assert not (root/'fma_portfolio/p7/model_worker.py').exists()
    assert not (root/'fma_portfolio/p7/model_executor.py').exists()
    app=(root/'app.py').read_text()
    assert 'Interactive forecast' in app and 'forecast_page()' in app


def test_owner_local_gate_requires_flag_and_loopback(monkeypatch):
    import sys
    from types import SimpleNamespace
    from fma_portfolio.p7.owner_local import owner_local_enabled
    class Config:
        def __init__(self, address): self.address=address
        def get_option(self, name):
            assert name=='server.address'
            return self.address
    monkeypatch.setenv('FMA_PORTFOLIO_OWNER_LOCAL','1')
    monkeypatch.setitem(sys.modules, 'streamlit', SimpleNamespace(config=Config('0.0.0.0')))
    assert not owner_local_enabled()
    monkeypatch.setitem(sys.modules, 'streamlit', SimpleNamespace(config=Config('127.0.0.1')))
    assert owner_local_enabled()
    monkeypatch.delenv('FMA_PORTFOLIO_OWNER_LOCAL')
    assert not owner_local_enabled()


def test_owner_launcher_environment_does_not_inherit_private_secrets(tmp_path, monkeypatch):
    from scripts.run_owner_local import build_owner_env
    monkeypatch.setenv('FMA_DATABASE_URL','postgresql://secret')
    monkeypatch.setenv('PRIVATE_API_KEY','not-a-real-key')
    env=build_owner_env(tmp_path,tmp_path/'science',tmp_path/'data')
    assert 'FMA_DATABASE_URL' not in env and 'PRIVATE_API_KEY' not in env
    assert env['FMA_PORTFOLIO_OWNER_LOCAL']=='1'


def test_original_owner_project_remains_outside_repository():
    from pathlib import Path
    repo=Path(__file__).resolve().parents[1]
    assert not (repo/'deployment/public_web/web_app/model_worker.py').exists()
    assert not (repo/'.env').exists()
    assert not (repo/'data/fixtures.csv').read_text().count('\n')>1


def test_owner_local_actual_child_protocol_with_stub(tmp_path, monkeypatch):
    """Transport smoke only: stub child proves subprocess plumbing; not model parity."""
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys
req=json.loads(sys.stdin.read());assert req["league"]=="E0"
print(json.dumps({"ok":True,"result":{"ah":{"status":"NO_SIGNAL","direction":None,"stake_u":None},"ou":{"status":"FORECAST","direction":"OVER","stake_u":1.0}}}))
''')
    monkeypatch.setattr('fma_portfolio.p7.owner_local.owner_local_enabled',lambda:True)
    monkeypatch.setattr('fma_portfolio.p7.owner_local._roots',lambda:(tmp_path,tmp_path,tmp_path,worker))
    result=predict(REQ,timeout_seconds=5)
    assert result['ah']['status']=='NO_SIGNAL'
    assert result['ou']['direction']=='OVER'


def test_p7_forecast_page_import_is_self_contained():
    """Public package must import without adding original P7 web_app to PYTHONPATH."""
    import subprocess
    import sys
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    script = (
        "import sys, types; "
        "sys.modules['streamlit'] = types.ModuleType('streamlit'); "
        "from fma_portfolio.p7.forecast_ui import forecast_page; "
        "assert callable(forecast_page)"
    )
    result = subprocess.run([sys.executable, '-c', script], cwd=repo,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
