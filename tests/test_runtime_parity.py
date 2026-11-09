"""P8.1C-2 tests use stubs only; they are not scientific Mac/Linux evidence."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from fma_portfolio.runtime_parity import (
    Roots, ParityError, SCHEMA_CASES, SCHEMA_BASELINE, canonical, digest_bytes,
    source_manifest, source_identity, load_cases, make_baseline, validate_baseline,
    compare_baseline, private_path, safe_write_private_json, interpreter_report,
)
from scripts.build_private_parity_cases import cases_from_export

ROOT=Path(__file__).resolve().parents[1]
REQ={
 'league':'E0','home':'Liverpool','away':'Fulham','fixture_date':'2026-11-21',
 'ah_line':-1.0,'ah_home_odds':1.93,'ah_away_odds':1.95,
 'asian_line':2.75,'asian_over_odds':1.9,'asian_under_odds':1.96,
 'fixed_over_odds':1.82,'fixed_under_odds':2.02,
}
SIGNAL={'ah':{'status':'FORECAST','direction':'HOME','stake_u':1.0},
        'ou':{'status':'FORECAST','direction':'UNDER','stake_u':1.0}}
NO={'ah':{'status':'NO_SIGNAL','direction':None,'stake_u':None},
    'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}}


def fake_roots(tmp_path: Path) -> Roots:
    roots=Roots(tmp_path/'private_project',tmp_path/'science',tmp_path/'data',Path(sys.executable))
    from fma_portfolio.runtime_parity import REQUIRED_SOURCE
    for key in REQUIRED_SOURCE:
        group,rel=key.split('/',1)
        where=getattr(roots,group)/rel
        where.parent.mkdir(parents=True,exist_ok=True)
        where.write_text('print("frozen science stub")\n')
    return roots


def cases(n=2):
    return [{'id':f'fixture_{i:02d}', 'request':{**REQ,'home':f'Home {i}','away':f'Away {i}'}}
            for i in range(n)]


def test_load_private_cases_and_reject_invalid(tmp_path):
    path=tmp_path/'cases.json'
    path.write_text(json.dumps({'schema':SCHEMA_CASES,'cases':cases()}))
    assert load_cases(path)==cases()
    assert len(set(digest_bytes(canonical(x['request'])) for x in load_cases(path))) == 2
    path.write_text(json.dumps({'schema':SCHEMA_CASES,'cases':[cases()[0],cases()[0]]}))
    with pytest.raises(ParityError,match='duplicate case id'):load_cases(path)
    wrong=cases()[0]
    wrong['request']['private_path']='/etc/secret'
    path.write_text(json.dumps({'schema':SCHEMA_CASES,'cases':[wrong]}))
    with pytest.raises(ParityError,match='exact 12'):load_cases(path)
    path.write_text(json.dumps({'schema':SCHEMA_CASES,'cases':cases()}))
    with pytest.raises(ParityError,match='Duplicate model input'):
        equal=cases();equal[1]['request']=equal[0]['request']
        path.write_text(json.dumps({'schema':SCHEMA_CASES,'cases':equal}))
        load_cases(path)


def test_private_evidence_never_inside_public_repository(tmp_path):
    with pytest.raises(ParityError,match='OUTSIDE'):
        private_path(ROOT/'data/unsafe.json',ROOT,should_exist=False)
    path=tmp_path/'output.json'
    safe_write_private_json(path,{'private':123},ROOT)
    assert path.stat().st_mode & 0o077 == 0
    with pytest.raises(ParityError,match='overwritten'):
        safe_write_private_json(path,{'private':456},ROOT)


def test_hash_source_inventory_and_detect_mutations(tmp_path):
    roots=fake_roots(tmp_path)
    first=source_manifest(roots)
    assert len(first)>=11
    from fma_portfolio.runtime_parity import REQUIRED_SOURCE
    assert set(REQUIRED_SOURCE).issubset(first)
    f=roots.project/'backend/public_factory.py'
    f.write_text('modified source')
    second=source_manifest(roots)
    assert first!=second
    f.unlink()
    with pytest.raises(ParityError,match='Required scientific component'):
        source_manifest(roots)


def test_reference_manifest_is_explicit_and_detects_modifications(tmp_path):
    roots=fake_roots(tmp_path)
    refs=tmp_path/'frozen_reference';refs.mkdir();(refs/'coefficients.csv').write_text('1,2,3')
    first=source_identity(roots,[refs],ROOT)
    assert first['reference_coverage']=='DECLARED_ROOTS_ONLY'
    assert len(first['reference_files'])==1
    assert len(first['source_sha256'])==64
    (refs/'coefficients.csv').write_text('4,5,6')
    second=source_identity(roots,[refs],ROOT)
    assert second['reference_sha256']!=first['reference_sha256']
    with pytest.raises(ParityError,match='no supported data'):
        empty=tmp_path/'empty';empty.mkdir();source_identity(roots,[empty],ROOT)


def test_baseline_strict_output_and_source_fail_closed(tmp_path):
    roots=fake_roots(tmp_path)
    identity=source_identity(roots,[],ROOT)
    inputs=cases()
    baseline=make_baseline(inputs,identity,lambda req:SIGNAL)
    assert validate_baseline(baseline)==baseline
    report=compare_baseline(baseline,inputs,identity,lambda req:SIGNAL,min_cases=2)
    assert report['parity_pass'] and report['output_matches']==2
    assert not report['promotion_candidate']  # not a reference-data audit
    assert not report['coverage_gate']
    mismatch=compare_baseline(baseline,inputs,identity,lambda req:NO,min_cases=2)
    assert not mismatch['parity_pass'] and mismatch['output_matches']==0
    stale=copy.deepcopy(identity);stale['source_sha256']='0'*64
    mismatch=compare_baseline(baseline,inputs,stale,lambda req:SIGNAL,min_cases=2)
    assert not mismatch['parity_pass'] and not mismatch['identity_checks']['scientific_source']
    bad=copy.deepcopy(baseline);bad['runtime']['source_sha256']='0'*64
    with pytest.raises(ParityError,match='manifest hash'):validate_baseline(bad)
    with pytest.raises(ParityError,match='input corpus'):
        altered=copy.deepcopy(inputs);altered[0]['request']['fixed_over_odds']=1.99
        compare_baseline(baseline,altered,identity,lambda req:SIGNAL)


def test_promotion_candidate_only_with_mac_linux_packages_references_and_diverse_outcomes(tmp_path):
    roots=fake_roots(tmp_path)
    refs=tmp_path/'refs';refs.mkdir();(refs/'ref.csv').write_text('frozen,coefficients')
    identity=source_identity(roots,[refs],ROOT)
    rows=cases(20)
    for i,row in enumerate(rows):
        row['request']['league']=('E0','D1','SP1','I1','F1')[i%5]
    def predict(req):return SIGNAL if int(req['home'].split(' ')[-1])%2==0 else NO
    baseline=make_baseline(rows,identity,predict)
    report=compare_baseline(baseline,rows,identity,predict,min_cases=20)
    assert report['coverage_gate'] and not report['promotion_candidate']
    assert not report['cross_platform_mac_linux']
    assert report['p50_wall_seconds']>=0
    # Explicitly model the two sides of the cross-platform check.  The
    # unmodified identity reflects the *current test host*: on a Mac it is
    # Darwin, on CI/Linux it is Linux.  Never rely on that for this gate.
    mac=copy.deepcopy(baseline)
    mac['runtime']['interpreter']['platform']='Darwin'
    linux=copy.deepcopy(identity)
    linux['interpreter']=copy.deepcopy(linux['interpreter'])
    linux['interpreter']['platform']='Linux'
    report=compare_baseline(mac,rows,linux,predict,min_cases=20)
    assert report['cross_platform_mac_linux'] and report['promotion_candidate']

    # Neither an insufficient case corpus nor same-platform verification may
    # qualify, even with identical scientific sources and simulated outputs.
    assert not compare_baseline(mac,rows,linux,predict,min_cases=21)['promotion_candidate']
    mac_verifier=copy.deepcopy(linux)
    mac_verifier['interpreter']['platform']='Darwin'
    same_host=compare_baseline(mac,rows,mac_verifier,predict,min_cases=20)
    assert not same_host['cross_platform_mac_linux']
    assert not same_host['promotion_candidate']
    drift=copy.deepcopy(linux)
    drift['interpreter']['python']='3.15.0'
    assert not compare_baseline(mac,rows,drift,predict,min_cases=20)['promotion_candidate']


def test_interpreter_version_probe(tmp_path):
    result=interpreter_report(Path(sys.executable))
    assert result['python'] and result['platform']
    assert isinstance(result['packages']['numpy'], (str,type(None)))


def test_extract_real_structure_from_fake_private_export(tmp_path):
    exported=tmp_path/'private-export.zip'
    def snapshot(index,league):
        return {'schema_version':'ANALYSIS_SNAPSHOT_V1','analysis_id':f'AN_{index:016x}',
                'fixture':{'league':league,'home_team':f'Home {index}','away_team':f'Away {index}',
                           'fixture_date':'2026-11-21'},
                'market_inputs':{
                    'ah':{'line':-0.5,'home_or_over_price':1.9,'away_or_under_price':1.95},
                    'ou_asian_main':{'line':2.75,'home_or_over_price':1.95,'away_or_under_price':1.9},
                    'ou_fixed25':{'line':2.5,'home_or_over_price':1.85,'away_or_under_price':2.05}}}
    with zipfile.ZipFile(exported,'w') as z:
        for index,league in enumerate(('E0','D1','SP1','I1','F1')):
            z.writestr(f'example/Private/analyses/AN_{index:016x}.json',json.dumps(snapshot(index,league)))
        z.writestr('example/Private/analyses/AN_bad.json','{}')
    extracted,rejected=cases_from_export(exported,count=5)
    assert len(extracted)==5 and rejected==1
    assert {r['request']['league'] for r in extracted}=={'E0','D1','SP1','I1','F1'}
    assert len({r['id'] for r in extracted})==5


def test_verify_cli_stub_runs_full_real_subprocess_protocol(tmp_path):
    roots=fake_roots(tmp_path)
    worker=roots.project/'deployment/public_web/web_app/model_worker.py'
    worker.write_text('''import json,sys
req=json.loads(sys.stdin.read())
assert req['league']=='E0'
print(json.dumps({'ok':True,'result':{'ah':{'status':'FORECAST','direction':'HOME','stake_u':1.0},'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}}}))
''')
    private_cases=tmp_path/'cases.json'
    private_cases.write_text(json.dumps({'schema':SCHEMA_CASES,'cases':cases()}))
    baseline_file=tmp_path/'baseline.json'
    verify_report=tmp_path/'report.json'
    base=[sys.executable,str(ROOT/'scripts/verify_scientific_runtime.py'),
          '--project-root',str(roots.project),'--science-root',str(roots.science),
          '--data-root',str(roots.data),'--model-python',sys.executable,
          '--cases',str(private_cases),'--baseline-file',str(baseline_file)]
    first=subprocess.run([*base[:2],'baseline',*base[2:]],capture_output=True,text=True,timeout=15)
    assert first.returncode==0,first.stderr
    assert baseline_file.is_file()
    second=subprocess.run([*base[:2],'verify',*base[2:], '--report-file',str(verify_report)],capture_output=True,text=True,timeout=15)
    assert second.returncode==0,second.stderr
    assert 'PARITY: PASS' in second.stdout
    assert 'PROMOTION-CANDIDATE GATE: NOT READY' in second.stdout
    assert json.loads(verify_report.read_text())['case_count']==2


def test_security_check_rejects_private_parity_json_even_if_renamed(tmp_path, monkeypatch):
    from scripts import security_check
    monkeypatch.setattr(security_check, 'ROOT', tmp_path)
    (tmp_path/'something_innocuous.json').write_text(json.dumps({
       'schema':'FMA_PRIVATE_RUNTIME_PARITY_CASES_V1','cases':[]}))
    failures=security_check.run()
    assert any('Private parity evidence must never be committed' in item for item in failures)


def test_extract_cli_reports_missing_zip_without_private_path_leak(tmp_path, capsys):
    from scripts.build_private_parity_cases import main
    secret_filename = 'TOP_SECRET_PRIVATE_FILE_DO_NOT_ECHO.zip'
    rc = main(['--analysis-export', str(tmp_path/secret_filename),
               '--output', str(tmp_path/'private.json'), '--count', '40'])
    error = capsys.readouterr().err
    assert rc == 2
    assert 'SOURCE_MISSING' in error
    assert secret_filename not in error


def test_extract_cli_reports_existing_output_without_overwriting(tmp_path, capsys):
    from scripts.build_private_parity_cases import main
    valid = tmp_path/'export.zip'
    # Invalid content is fine here: output must never be overwritten.
    with zipfile.ZipFile(valid, 'w') as archive:
        archive.writestr('export/Private/analyses/AN_bad.json', '{}')
    out = tmp_path/'private.json'
    out.write_text('existing evidence')
    rc = main(['--analysis-export', str(valid), '--output', str(out)])
    error = capsys.readouterr().err
    assert rc == 2 and 'OUTPUT_EXISTS' in error
    assert out.read_text() == 'existing evidence'


def test_extract_cli_reports_missing_output_directory(tmp_path, capsys):
    from scripts.build_private_parity_cases import main
    valid = tmp_path/'export.zip'
    with zipfile.ZipFile(valid, 'w') as archive:
        archive.writestr('export/Private/analyses/AN_bad.json', '{}')
    rc = main(['--analysis-export', str(valid),
               '--output', str(tmp_path/'missing'/'private.json')])
    assert rc == 2 and 'OUTPUT_PARENT_MISSING' in capsys.readouterr().err
