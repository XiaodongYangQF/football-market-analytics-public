"""P8.1B Public Portfolio integration of the genuine P7.4 forecast form.

Owner-local execution stays loopback-only. Hosted mode is an
OIDC allowlisted, disabled-by-default pilot behind a protected model gateway. Saved previews are browser-session only, never official P&L.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import csv
import io
import os

import streamlit as st
from .fixtures_store import load_fixtures, fixture_options, team_options
from .fixture_source import fixture_source
from .forecast_contract import validate_request, InvalidForecastInput
from fma_portfolio.eligibility import classify_fixture
from .owner_local import predict, ForecastUnavailable, ForecastIneligible, owner_local_enabled
from fma_portfolio.hosted_client import hosted_authorized, hosted_configured, predict_hosted
from .saved_forecasts import (create_record, archive_json, archive_csv, parse_archive,
                             merge_records, row_for_display, SavedForecastsError)
from .public_theme import (apply_public_theme, sidebar_brand, page_hero, section_header,
                          market_card_header, selected_match, forecast_card, overview_kpi_cards)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data'
LEAGUES = {'Premier League':'E0','Bundesliga':'D1','La Liga':'SP1',
           'Serie A':'I1','Ligue 1':'F1'}



def _price(label: str, key: str):
    return st.number_input(label, min_value=1.01, max_value=1000.0, value=None,
                           step=0.01, format='%.3f', key=key, placeholder='e.g. 1.950')


def _match_picker() -> tuple[str, str, str, date, str, str]:
    """Same 2-row match selector as Local Public, from a separate public fixture CSV.

    Returns (league, canonical_home, canonical_away, date, display_home, display_away).
    """
    section_header('01', 'Choose a match', 'Pick a fixture from the schedule or enter teams manually.')
    c1,c2 = st.columns(2, gap='medium')
    with c1:
        league_label = st.selectbox('Competition', tuple(LEAGUES), key='pub_competition')
    with c2:
        mode = st.radio('Selection method', ('From schedule','Manual match'),
                        horizontal=True, key='pub_match_mode')
    league = LEAGUES[league_label]
    schedule_path, uses_owner_schedule = fixture_source(
        DATA / 'fixtures.csv', owner_local=owner_local_enabled(),
        project_root=os.environ.get('FMA_WEB_PROJECT_ROOT'))
    try:
        scheduled = load_fixtures(schedule_path, league)
    except (OSError, ValueError):
        st.error('Fixture schedule could not be read. Please use Manual match.')
        scheduled = []
    if uses_owner_schedule:
        st.caption('Owner-local: using the existing P7 Public schedule (not bundled in GitHub).')
    if mode == 'From schedule':
        wc,fc = st.columns(2, gap='medium')
        with wc:
            window = st.segmented_control('Fixture window', ('Upcoming','All'),
                                          default='Upcoming', key='pub_fixture_window')
            options = fixture_options(scheduled, window or 'Upcoming', date.today())
            st.caption(f'{len(options)} fixtures shown · {len(scheduled)} in league')
        with fc:
            if options:
                ix = st.selectbox('Fixture', range(len(options)),
                      format_func=lambda i:(f"{date.fromisoformat(options[i]['fixture_date']):%d %b %Y} · "
                                            f"{options[i]['home']} vs {options[i]['away']}"),
                      key='pub_fixture_pick')
                f=options[ix]
            else:
                if not scheduled:
                    st.info('No fixtures in this schedule. Owner-local: check the original P7 Public '
                            'fixtures.csv. Hosted version: use Manual match.')
                else:
                    st.info('No upcoming fixtures in the schedule. Choose All or Manual match.')
                f=None
        if f is not None:
            selected_match(f['home'],f['away'],league_label,f['fixture_date'])
            return (league,f['canonical_home'],f['canonical_away'],
                    date.fromisoformat(f['fixture_date']),f['home'],f['away'])
        return league,'','',date.today(),'',''
    # Manual mode mirrors the Local Public row layout: date/home/away.
    dc,hc,ac=st.columns(3,gap='medium')
    with dc: when=st.date_input('Match date',value=date.today(),key='pub_match_date')
    try:
        teams=team_options(scheduled)
    except ValueError:
        teams=[]
    lookup=dict(teams)
    with hc:
        if teams:
            home_display=st.selectbox('Home team', ('', *(s for s,_ in teams)),key='pub_home_team')
        else:
            home_display=st.text_input('Home team',key='pub_home_text',max_chars=100)
    with ac:
        if teams:
            away_display=st.selectbox('Away team', ('', *(s for s,_ in teams if s!=home_display)),
                                      key='pub_away_team')
        else:
            away_display=st.text_input('Away team',key='pub_away_text',max_chars=100)
    if home_display and away_display:
        selected_match(home_display,away_display,league_label,when.isoformat())
    return (league,lookup.get(home_display,home_display),lookup.get(away_display,away_display),
            when,home_display,away_display)


def _result_card(market: str, line: float, item: dict, *,home: str,away: str) -> None:
    status, side=item.get('status'),item.get('direction')
    if status=='FORECAST' and side in ('HOME','AWAY','OVER','UNDER'):
        label={'HOME':home,'AWAY':away,'OVER':f'OVER {line:.2f}',
               'UNDER':f'UNDER {line:.2f}'}[side]
        context={'HOME':'Home handicap side', 'AWAY':'Away handicap side',
                 'OVER':'Asian main total direction','UNDER':'Asian main total direction'}[side]
        weight=item.get('stake_u')
        if weight != 1.0:
            st.error('Unexpected strategy weight; forecast cannot be displayed.')
            return
        forecast_card(market, f'{line:+.2f}' if market=='Asian Handicap' else f'{line:.2f} goals',
                      label,context,status='FORECAST',weight=1.0)
    elif status=='NO_SIGNAL':
        forecast_card(market, f'{line:+.2f}' if market=='Asian Handicap' else f'{line:.2f} goals',
                      'NO SIGNAL','No model direction for these inputs',status='NO_SIGNAL',weight=None)
    else:
        forecast_card(market, f'{line:+.2f}' if market=='Asian Handicap' else f'{line:.2f} goals',
                      'UNAVAILABLE','Unable to generate a forecast',status='UNAVAILABLE',weight=None)


def _saved_records() -> list[dict]:
    return st.session_state.setdefault('web_saved_forecasts', [])


def _save_records(incoming: list[dict]) -> int:
    existing=st.session_state.setdefault('web_saved_forecasts', [])
    merged,count=merge_records(existing,incoming)
    st.session_state['web_saved_forecasts']=merged
    return count


def _forecast_history_panel():
    section_header('04','Saved forecasts',
        'Your saved prematch snapshots. These are not settled results or official performance.')
    st.caption('Saved forecasts stay in this browser session. Export JSON to keep them, '
               'and restore it later. These records do not enter official P&L.')
    try:
        records=_saved_records()
    except SavedForecastsError as exc:
        st.error(f'Cannot read saved forecasts: {exc}')
        return
    if records:
        search=st.text_input('Find a saved fixture',key='web_saved_find',
                             placeholder='Team or competition')
        lower=search.casefold().strip()
        matching=[r for r in records if not lower or lower in
                  f"{r['home_team']} {r['away_team']} {r['competition']}".casefold()]
        matching=sorted(matching,key=lambda r:(r['saved_at_utc'],r['record_id']),reverse=True)
        st.caption(f'{len(matching)} shown · {len(records)} saved in archive')
        st.dataframe([row_for_display(r) for r in matching[:500]],
                     use_container_width=True,hide_index=True)
        if len(matching)>500:
            st.caption('Showing the newest 500 matching rows; downloads include all matching records.')
        dl1,dl2=st.columns(2,gap='small')
        with dl1:
            st.download_button('Download history (CSV)', archive_csv(matching),
                               file_name='fma_saved_forecasts.csv',
                               mime='text/csv',use_container_width=True,
                               key='web_saved_export_csv')
        with dl2:
            st.download_button('Backup / export (JSON)',archive_json(records),
                               file_name='fma_saved_forecasts.json',
                               mime='application/json',use_container_width=True,
                               key='web_saved_export_json')
    else:
        st.info('No saved forecasts yet. Generate a forecast, then choose Save forecast.')
    with st.expander('Restore a saved JSON history file',expanded=False):
        st.caption('Imports only P7.4 saved-forecast exports. Never imports trades into official performance.')
        uploaded=st.file_uploader('Choose a saved history JSON',type=['json'],
                                  key='web_saved_restore_file',max_upload_size=4)
        if st.button('Restore history',disabled=uploaded is None,key='web_saved_restore_btn'):
            try:
                rows=parse_archive(uploaded.getvalue())
                count=_save_records(rows)
            except (SavedForecastsError,OSError) as exc:
                st.error(f'History was not imported: {exc}')
            else:
                st.success(f'Imported {count} new records. Existing saved entries were preserved.')
                st.rerun()


def forecast_page():
    page_hero('Prematch Market Forecast',
              kicker='FOOTBALL MARKET ANALYTICS · PUBLIC',
              subtitle='Select a fixture, provide the AH and OU prices, and explore model-generated market forecasts.')
    local = owner_local_enabled()
    hosted = not local and hosted_authorized(getattr(st, 'user', None))
    if not local and not hosted:
        if hosted_configured():
            st.info('Hosted prediction pilot is restricted to authenticated, allowlisted research accounts. Public visitors can browse the forecast archive and performance; no demo predictions are fabricated.')
            signed_in = bool(getattr(getattr(st, 'user', None), 'is_logged_in', False))
            if not signed_in and hasattr(st, 'login'):
                if st.button('Sign in for research pilot', key='pub_hosted_sign_in'):
                    st.login()
        else:
            st.info('Hosted real-time forecasts are not enabled. Owner-local Mac mode can run the existing frozen model; no substitute predictions are generated.')
    if hosted:
        st.caption('Authenticated prediction pilot · real frozen model · server-side quota applies.')
    _,workflow,_=st.columns([1,10,1],gap='small')
    with workflow:
        with st.container(border=True,key='pub_match_picker_panel'):
            league,home,away,when,show_home,show_away=_match_picker()
        selection=(league,home,away,when.isoformat())
        if st.session_state.get('web_last_selection') != selection:
            st.session_state.pop('web_last_generated_forecast',None)
            st.session_state['web_last_selection']=selection
        coverage = classify_fixture(league, home, away, when)
        if home and away:
            if coverage.status == 'INELIGIBLE':
                st.warning(f'Forecast unavailable · {coverage.season}: {coverage.promoted_team} is a current-season promoted club outside the frozen model coverage. This is INELIGIBLE, not NO SIGNAL.')
            elif coverage.status == 'UNVERIFIED':
                st.warning('Coverage could not be verified for this season / team pairing. Forecast is disabled; no NO SIGNAL is recorded.')
        section_header('02','Market inputs','Three market quotes · decimal odds.')
        with st.form('public_forecast_inputs',clear_on_submit=False):
            with st.container(border=True):
                market_card_header('Asian Handicap','Current handicap line and both market prices.',badge='AH',kind='blue')
                c1,c2,c3=st.columns(3,gap='small')
                with c1:ah_line=st.number_input('Home handicap line',value=None,step=.25,format='%.2f',key='pub_ah_line')
                with c2:ah_home=_price('Home odds','pub_ah_home')
                with c3:ah_away=_price('Away odds','pub_ah_away')
            with st.container(border=True):
                market_card_header('Asian Total','Main Asian Total line and market prices.',badge='OU',kind='blue')
                c1,c2,c3=st.columns(3,gap='small')
                with c1:asian_line=st.number_input('Asian Total line',min_value=.5,max_value=6.,value=None,step=.25,format='%.2f',key='pub_ou_line')
                with c2:asian_over=_price('Over odds','pub_ou_over')
                with c3:asian_under=_price('Under odds','pub_ou_under')
            with st.container(border=True):
                market_card_header('Fixed 2.5 goals','Calibration reference used for the main OU line. Not a separate forecast.',badge='2.5',kind='neutral')
                c1,c2=st.columns(2,gap='small')
                with c1:fixed_over=_price('Over 2.5 odds','pub_fixed_over')
                with c2:fixed_under=_price('Under 2.5 odds','pub_fixed_under')
            submit=st.form_submit_button('Generate AH & OU forecasts',type='primary',use_container_width=True,disabled=(not (local or hosted) or coverage.status != 'ELIGIBLE'))
        if submit:
            try:
                request=validate_request({'league':league,'home':home,'away':away,'fixture_date':when,
                    'ah_line':ah_line,'ah_home_odds':ah_home,'ah_away_odds':ah_away,
                    'asian_line':asian_line,'asian_over_odds':asian_over,'asian_under_odds':asian_under,
                    'fixed_over_odds':fixed_over,'fixed_under_odds':fixed_under})
                with st.spinner('Computing model forecasts...'):
                    result=predict(request) if local else predict_hosted(request)
                competition=next(k for k,v in LEAGUES.items() if v==league)
                record=create_record(request,result,competition=competition,
                                     display_home=show_home,display_away=show_away)
                st.session_state['web_last_generated_forecast']=record
            except ForecastIneligible:
                st.warning('Fixture is outside the frozen model coverage. No forecast or NO SIGNAL record was created.')
                st.session_state.pop('web_last_generated_forecast',None)
            except InvalidForecastInput as exc:
                st.warning(str(exc))
                st.session_state.pop('web_last_generated_forecast',None)
            except ForecastUnavailable:
                st.warning('Frozen model unavailable in this environment. No prediction was generated.')
                st.session_state.pop('web_last_generated_forecast',None)
            except SavedForecastsError as exc:
                st.error(f'Invalid public forecast result: {exc}')
                st.session_state.pop('web_last_generated_forecast',None)
        latest=st.session_state.get('web_last_generated_forecast')
        if latest:
            section_header('03','Forecast results','Last generated forecast · Public V2 · 1u per signal.')
            st.caption(f"{latest['home_team']} vs {latest['away_team']} · "
                       f"{latest['fixture_date']} · {latest['competition']} · "
                       f"Generated {latest['saved_at_utc']}")
            ah={'status':latest['ah_status'],'direction':latest['ah_direction'],
                'stake_u':latest['ah_stake_u']}
            ou={'status':latest['ou_status'],'direction':latest['ou_direction'],
                'stake_u':latest['ou_stake_u']}
            left,right=st.columns(2,gap='large')
            with left:_result_card('Asian Handicap',latest['ah_line'],ah,
                                   home=latest['home_team'],away=latest['away_team'])
            with right:_result_card('Asian Total',latest['asian_line'],ou,
                                    home=latest['home_team'],away=latest['away_team'])
            c1,c2=st.columns(2,gap='small')
            with c1:
                if st.button('Save forecast to history',key='web_save_forecast',
                             use_container_width=True,type='primary'):
                    try:
                        added=_save_records([latest])
                    except (SavedForecastsError,OSError) as exc:
                        st.error(f'Could not save forecast: {exc}')
                    else:
                        st.success('Forecast saved.' if added else 'This forecast was already saved.')
            with c2:
                st.download_button('Download this forecast (CSV)', archive_csv([latest]),
                                   file_name='fma_current_forecast.csv',mime='text/csv',
                                   key='web_single_export',use_container_width=True)
            st.markdown('<p class="fma-pub-footnote">Public V2 uses the frozen rule signals; '
                        'AH-A and OU-B are reversed. Fixed 2.5 is a calibration input, not a '
                        'third forecast. All active signals are 1u. These records are unverified '
                        'prematch snapshots, not settled performance or betting advice.</p>',
                        unsafe_allow_html=True)
        _forecast_history_panel()

