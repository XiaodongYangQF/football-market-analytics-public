"""P8.1C-2E: season-frozen promotion gate / parity preservation."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import json

import pytest

from fma_portfolio.eligibility import classify_fixture, load_policy, EligibilityPolicyError
from fma_portfolio.p7.owner_local import ForecastIneligible
from scripts import eligible_mac_baseline as eb
from scripts import resumable_mac_baseline as rb
from fma_portfolio.runtime_parity import Roots, source_identity, REQUIRED_SOURCE
from fma_portfolio.p7.owner_local import ForecastUnavailable
from scripts.publish_prematch_receipt import check_selected_coverage
from fma_portfolio.prematch_receipts import ReceiptError

ROOT=Path(__file__).resolve().parents[1]
BASE={
 'league':'D1','home':'Freiburg','away':'Schalke 04','fixture_date':'2026-10-11',
 'ah_line':-1.,'ah_home_odds':1.90,'ah_away_odds':1.95,
 'asian_line':2.75,'asian_over_odds':1.91,'asian_under_odds':1.93,
 'fixed_over_odds':1.91,'fixed_under_odds':1.92,
}
PROMOTED = {
 'E0':['Coventry City','Hull City','Ipswich Town'],
 'D1':['Schalke 04','SV Elversberg','Paderborn'],
 'SP1':['Racing Santander','Deportivo A Coruña','Málaga'],
 'I1':['Venezia','Frosinone','AC Monza'],
 'F1':['Le Mans FC','ESTAC Troyes'],
}
NORMAL={
 'E0':('Leeds','Tottenham'),
 'D1':('Freiburg','Leverkusen'),
 'SP1':('Barcelona','Getafe'),
 'I1':('Milan','Inter'),
 'F1':('Lens','Marseille'),
}

@pytest.mark.parametrize('league,team',[(league,team) for league,teams in PROMOTED.items() for team in teams])
def test_all_promoted_clubs_are_ineligible_on_both_sides(league,team):
    normal=NORMAL[league][0]
    for home,away in ((normal,team),(team,normal)):
        status=classify_fixture(league,home,away,'2026-11-09')
        assert status.status=='INELIGIBLE' and status.reason=='PROMOTED_TEAM_2026_27'

@pytest.mark.parametrize('league,teams',list(NORMAL.items()))
def test_existing_clubs_are_eligible(league,teams):
    status=classify_fixture(league,*teams,'2026-11-09')
    assert status.status=='ELIGIBLE'

@pytest.mark.parametrize('fixture',[
 ('D1','Freiburg','Schalke 04','2026-10-11','INELIGIBLE'),
 ('I1','Lazio','Monza','2026-11-08','INELIGIBLE'),
 ('D1','FC Koln','Leverkusen','2026-10-11','ELIGIBLE'),
 ('D1','Köln','Leverkusen','2026-10-11','ELIGIBLE'),
 ('D1','Freiburg','NotInRoster','2026-10-11','UNVERIFIED'),
 ('D1','Freiburg','Leverkusen','2027-08-11','UNVERIFIED'),
 ('D1','Freiburg','Leverkusen','2025-11-11','UNVERIFIED'),
 ('D1','Schalke 04','Leverkusen','2025-11-11','UNVERIFIED'),
 ('E0','Schalke 04','Arsenal','2026-11-11','UNVERIFIED'),
])
def test_season_and_alias_contract(fixture):
    *inputs,expected=fixture
    assert classify_fixture(*inputs).status==expected


def test_policy_corruption_fails_closed(tmp_path):
    p=tmp_path/'policy.json'
    p.write_text('{broken')
    with pytest.raises(EligibilityPolicyError):load_policy(p)
    policy=copy.deepcopy(load_policy())
    policy['leagues']['D1']['promoted']=['Schalke 04','Elversberg','Unknown Club']
    p.write_text(json.dumps(policy))
    with pytest.raises(EligibilityPolicyError):load_policy(p)
    assert classify_fixture('D1','Freiburg','Schalke 04','2026-11-11',policy=None).status=='INELIGIBLE'


def test_owner_local_rejects_promoted_before_scientific_roots(monkeypatch):
    from fma_portfolio.p7 import owner_local
    monkeypatch.setattr(owner_local,'owner_local_enabled',lambda:True)
    monkeypatch.setattr(owner_local,'_roots',lambda:(_ for _ in ()).throw(AssertionError('science must never start')))
    with pytest.raises(ForecastIneligible) as exc:
        owner_local.predict(BASE)
    assert exc.value.reason=='PROMOTED_TEAM_2026_27'


def test_hosted_gateway_rejects_promoted_without_admission():
    from tests.test_hosted_prediction import running_gateway, post, GatewayState, TOKEN, RESULT
    # The executor must not run; policy screening takes place before quota admission.
    hits=[]
    with running_gateway(GatewayState(token=TOKEN,executor=lambda req:hits.append(req) or RESULT)) as server:
        status,response=post(server,request=BASE)
        assert status==422
        assert response=={'error':'fixture_ineligible','reason':'PROMOTED_TEAM_2026_27'}
        unknown=copy.deepcopy(BASE)
        unknown['away']='Unknown Club'
        assert post(server,request=unknown)[0]==422
    assert hits==[]


def test_new_receipts_are_blocked_but_existing_archive_schema_is_unchanged():
    assert check_selected_coverage([{'competition':'Bundesliga','home_team':'Köln',
                                    'away_team':'Leverkusen','fixture_date':'2026-11-14'}]) is None
    with pytest.raises(ReceiptError,match='PROMOTED_TEAM'):
        check_selected_coverage([{'competition':'Bundesliga','home_team':'Freiburg',
                                 'away_team':'Schalke 04','fixture_date':'2026-11-14'}])


def test_filtered_plan_keeps_original_indices_and_exclusion_reasons():
    rows=[{'id':f'case-{i}','request':{**BASE,'home':h,'away':a,'league':lg}}
          for i,(lg,h,a) in enumerate([
              ('E0','Leeds','Tottenham'),('I1','Lazio','Monza'),
              ('D1','Freiburg','Schalke 04'),('SP1','Barcelona','Getafe')],1)]
    eligible,excluded,unverified=eb.plan(rows,load_policy())
    assert [i for i,_ in eligible]==[1,4]
    assert [r['index'] for r in excluded]==[2,3]
    assert len(unverified)==0
    doc=eb.coverage_doc(rows,eligible,excluded,unverified,'0'*64)
    assert doc['original_case_count']==4 and doc['excluded_count']==2
    assert 'odds' not in str(doc)


def test_filtered_executor_reuses_checkpoint_at_original_position(tmp_path):
    from fma_portfolio.runtime_parity import REQUIRED_SOURCE
    roots=Roots(tmp_path/'private',tmp_path/'science',tmp_path/'data',Path(sys.executable))
    for name in REQUIRED_SOURCE:
        group,rest=name.split('/',1)
        f=getattr(roots,group)/rest
        f.parent.mkdir(parents=True,exist_ok=True)
        f.write_text('print(1)')
    identity=source_identity(roots,[],ROOT)
    folder=rb.make_private_checkpoint_dir(tmp_path/'checkpoints',ROOT)
    signal={'ah':{'status':'FORECAST','direction':'HOME','stake_u':1.0},
            'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}}
    eligible=[(1,{'id':'one','request':{**BASE,'league':'E0','home':'Leeds','away':'Tottenham'}}),
              (4,{'id':'four','request':{**BASE,'league':'SP1','home':'Barcelona','away':'Getafe'}})]
    rb.save_case(rb.checkpoint_filename(folder,1),index=1,case=eligible[0][1],
                 identity=identity,result=signal,wall_seconds=11.2,repo_root=ROOT)
    called=[]
    got=eb.run_eligible(eligible,identity,checkpoint_dir=folder,repo_root=ROOT,
                        run_model=lambda req:called.append(req['home']) or signal)
    assert len(got)==2 and called==['Barcelona']
    assert rb.checkpoint_filename(folder,1).exists()
    assert rb.checkpoint_filename(folder,4).exists()
    assert not rb.checkpoint_filename(folder,2).exists()


def test_eligible_cli_creates_filtered_private_baseline_and_preserves_indices(tmp_path):
    """End-to-end protected subprocess protocol with a stub, not model parity."""
    from fma_portfolio.runtime_parity import SCHEMA_CASES, validate_baseline
    roots=Roots(tmp_path/'private',tmp_path/'science',tmp_path/'data',Path(sys.executable))
    for name in REQUIRED_SOURCE:
        group,rest=name.split('/',1)
        target=getattr(roots,group)/rest
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('print("stub")')
    worker=roots.project/'deployment/public_web/web_app/model_worker.py'
    worker.write_text('''import sys,json
json.loads(sys.stdin.read())
print(json.dumps({"ok":True,"result":{"ah":{"status":"FORECAST","direction":"HOME","stake_u":1.0},"ou":{"status":"NO_SIGNAL","direction":None,"stake_u":None}}}))
''')
    rows=[
        {'id':'a','request':{**BASE,'league':'E0','home':'Leeds','away':'Tottenham'}},
        {'id':'b','request':BASE},
        {'id':'c','request':{**BASE,'league':'SP1','home':'Barcelona','away':'Getafe'}},
    ]
    p=tmp_path/'cases.json'
    p.write_text(json.dumps({'schema':SCHEMA_CASES,'cases':rows}))
    base=['--cases',str(p),'--project-root',str(roots.project),
          '--science-root',str(roots.science),'--data-root',str(roots.data),
          '--checkpoint-dir',str(tmp_path/'checkpoints'),
          '--eligible-cases-file',str(tmp_path/'eligible_cases.json'),
          '--coverage-file',str(tmp_path/'eligibility_coverage.json'),
          '--baseline-file',str(tmp_path/'mac_baseline_eligible.json'),
          '--model-python',sys.executable,'--max-case-seconds','10']
    assert eb.main([*base,'--plan-only'])==0
    assert not (tmp_path/'checkpoints').exists()
    assert eb.main(base)==0
    eligible=json.loads((tmp_path/'eligible_cases.json').read_text())
    assert [x['id'] for x in eligible['cases']]==['a','c']
    assert (tmp_path/'checkpoints'/'case_001.json').exists()
    assert not (tmp_path/'checkpoints'/'case_002.json').exists()
    assert (tmp_path/'checkpoints'/'case_003.json').exists()
    assert len(validate_baseline(json.loads((tmp_path/'mac_baseline_eligible.json').read_text()))['cases'])==2
    assert eb.main(base)==2  # fail closed, never overwrite saved evidence
