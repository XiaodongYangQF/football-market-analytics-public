"""Public presentation system: shared FMA typography, isolated adaptive colors.

This module contains *only* layout and accessible presentational HTML.
The Streamlit UI is intentionally separate from the Private theme and writers.
"""
from __future__ import annotations

import html
import streamlit as st


PUBLIC_THEME_CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;450;500;550;600;650;700;750&family=Montserrat:wght@500;600;650;700;750;800&display=swap');

/* Theme-aware: never pin the page to one dark or light background. */
.block-container {
    max-width: 1180px;
    margin-inline: auto;
    padding: 1.15rem 2.25rem 4rem;
}
.stApp { font-family: 'Inter', system-ui, sans-serif; }
[data-testid="stSidebar"] {
    min-width: 245px;
    max-width: 245px;
    border-right: 1px solid color-mix(in srgb, currentColor 12%, transparent);
}
[data-testid="stSidebarContent"] { padding-top: 1.2rem; }
/* Reduce harsh default borders while retaining visible component separation. */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 18px !important;
    border-color: color-mix(in srgb, currentColor 13%, transparent) !important;
    background: color-mix(in srgb, currentColor 2%, transparent);
    box-shadow: 0 9px 30px color-mix(in srgb, currentColor 4%, transparent);
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stDateInput"] input {
    border-radius: 11px !important;
}
.stButton > button,
[data-testid="stFormSubmitButton"] > button {
    border-radius: 12px;
    font-family: 'Inter', system-ui, sans-serif;
    font-weight: 700;
    min-height: 2.9rem;
    transition: transform .14s ease, box-shadow .14s ease;
}
[data-testid="stFormSubmitButton"] > button:hover { transform: translateY(-1px); }
[data-testid="stWidgetLabel"] p { font-weight: 600; font-size: .87rem; }
[data-testid="stRadio"] { padding-top: .28rem; }
[data-testid="stSegmentedControl"] { margin-bottom: .15rem; }

.fma-pub-sidebar {
    padding: .5rem .3rem .9rem;
    font-family: 'Inter', system-ui, sans-serif;
}
.fma-pub-sidebar-mark {
    display: inline-flex;
    width: 42px;
    height: 42px;
    align-items: center;
    justify-content: center;
    border: 1px solid color-mix(in srgb, var(--primary-color, #4e9ce5) 34%, transparent);
    border-radius: 13px;
    background: color-mix(in srgb, var(--primary-color, #4e9ce5) 13%, transparent);
    font-family: 'Montserrat', system-ui, sans-serif;
    letter-spacing: -.03em;
    font-weight: 800;
    font-size: .92rem;
}
.fma-pub-sidebar-name {
    margin-top: 1rem;
    font-family: 'Montserrat', system-ui, sans-serif;
    font-size: .86rem;
    font-weight: 750;
    letter-spacing: -.012em;
    line-height: 1.45;
}
.fma-pub-sidebar-label {
    margin-top: .3rem;
    letter-spacing: .13em;
    text-transform: uppercase;
    opacity: .62;
    font-weight: 700;
    font-size: .63rem;
}
.fma-pub-sidebar-rule {
    height: 1px;
    margin: 1.5rem 0 1rem;
    background: color-mix(in srgb, currentColor 13%, transparent);
}
.fma-pub-sidebar-section { font-size: .72rem; opacity: .65; font-weight: 650; letter-spacing: .04em; }
.fma-pub-sidebar-active {
    margin: .7rem 0 1.15rem;
    border-left: 3px solid var(--primary-color, #4e9ce5);
    padding: .7rem .8rem;
    background: color-mix(in srgb, currentColor 5%, transparent);
    border-radius: 0 10px 10px 0;
    font-size: .87rem;
    font-weight: 700;
}
.fma-pub-sidebar-note { opacity: .69; font-size: .77rem; line-height: 1.7; }

.fma-public-hero {
    position: relative;
    overflow: hidden;
    margin-bottom: 1.45rem;
    padding: 1.85rem 2rem 1.9rem;
    border-radius: 20px;
    border: 1px solid color-mix(in srgb, var(--primary-color, #4e9ce5) 22%, currentColor 9%);
    background: color-mix(in srgb, currentColor 3.5%, transparent);
    box-shadow: 0 12px 32px color-mix(in srgb, currentColor 4%, transparent);
}
.fma-public-hero::after {
    content: '';
    position: absolute;
    pointer-events: none;
    width: 280px;
    height: 280px;
    right: -40px;
    top: -175px;
    border-radius: 50%;
    background: radial-gradient(circle, color-mix(in srgb, var(--primary-color, #4e9ce5) 19%, transparent), transparent 72%);
}
.fma-public-kicker {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: .5rem;
    margin-bottom: .85rem;
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .14em;
    text-transform: uppercase;
    opacity: .78;
}
.fma-public-kicker::before {
    content: '';
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--primary-color, #4e9ce5);
    box-shadow: 0 0 0 4px color-mix(in srgb, var(--primary-color, #4e9ce5) 14%, transparent);
}
.fma-public-title {
    position: relative;
    z-index: 1;
    font-family: 'Montserrat', 'Inter', system-ui, sans-serif;
    font-weight: 800;
    font-size: clamp(1.7rem, 3vw, 2.55rem);
    line-height: 1.17;
    letter-spacing: -.043em;
    margin: 0 0 .65rem;
}
.fma-public-copy {
    max-width: 790px;
    font-size: .92rem;
    line-height: 1.65;
    opacity: .77;
}
.fma-pub-hero-pills { display: flex; flex-wrap: wrap; gap: .52rem; margin-top: 1.25rem; }
.fma-pub-pill {
    border-radius: 30px;
    border: 1px solid color-mix(in srgb, currentColor 15%, transparent);
    padding: .35rem .72rem;
    font-size: .7rem;
    letter-spacing: .035em;
    font-weight: 700;
    opacity: .83;
}
.fma-pub-pill:first-child {
    border-color: color-mix(in srgb, var(--primary-color, #4e9ce5) 40%, transparent);
    background: color-mix(in srgb, var(--primary-color, #4e9ce5) 10%, transparent);
    opacity: 1;
}
.fma-pub-section {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: .8rem;
    margin: 1.3rem 0 .8rem;
}
.fma-pub-step {
    width: 35px;
    height: 35px;
    border-radius: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: color-mix(in srgb, var(--primary-color, #4e9ce5) 14%, transparent);
    border: 1px solid color-mix(in srgb, var(--primary-color, #4e9ce5) 25%, transparent);
    font: 800 .8rem/1 'Montserrat', sans-serif;
}
.fma-pub-section-title {
    font: 750 1.14rem/1.35 'Montserrat', 'Inter', system-ui, sans-serif;
    letter-spacing: -.027em;
}
.fma-pub-section-copy { font-size: .78rem; opacity: .66; line-height: 1.55; }
.fma-pub-section-line { flex: 1; height: 1px; min-width: 24px; background: color-mix(in srgb, currentColor 11%, transparent); }
.fma-public-market-head {
    display: grid;
    grid-template-columns: auto 1fr;
    column-gap: .85rem;
    align-items: center;
    padding: .25rem 0 1rem;
    margin-bottom: .3rem;
    border-bottom: 1px solid color-mix(in srgb, currentColor 11%, transparent);
}
.fma-public-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 48px;
    height: 45px;
    border: 1px solid color-mix(in srgb, var(--primary-color, #4e9ce5) 32%, transparent);
    border-radius: 12px;
    background: color-mix(in srgb, var(--primary-color, #4e9ce5) 10%, transparent);
    font: 750 .73rem/1 'Montserrat', system-ui, sans-serif;
    letter-spacing: .05em;
}
.fma-public-market-title {
    font: 750 1.05rem/1.35 'Montserrat', 'Inter', system-ui, sans-serif;
    letter-spacing: -.024em;
}
.fma-public-market-subtitle { opacity: .68; font-size: .78rem; line-height: 1.5; margin-top: .18rem; }
.fma-pub-calibration {
    display: inline-flex;
    gap: .45rem;
    align-items: center;
    margin-top: .75rem;
    font-size: .75rem;
    opacity: .7;
}
.fma-pub-calibration::before { content: '●'; color: var(--primary-color, #4e9ce5); font-size: .6rem; }
.fma-pub-match-strip {
    margin: .9rem 0 0;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: .7rem 1.2rem;
    border: 1px solid color-mix(in srgb, currentColor 10%, transparent);
    border-radius: 12px;
    padding: .8rem 1rem;
    background: color-mix(in srgb, currentColor 3.2%, transparent);
}
.fma-pub-match-label { font-size: .67rem; letter-spacing: .1em; text-transform: uppercase; font-weight: 750; opacity: .6; }
.fma-pub-match-teams { font: 750 .93rem/1.5 'Montserrat', 'Inter', system-ui, sans-serif; letter-spacing: -.025em; }
.fma-pub-match-meta { font-size: .78rem; opacity: .75; white-space: nowrap; }
.fma-pub-results-meta { font-size: .84rem; opacity: .74; margin: -.4rem 0 1rem; }
.fma-pub-result {
    position: relative;
    height: 100%;
    min-height: 202px;
    padding: 1.4rem 1.55rem;
    border: 1px solid color-mix(in srgb, currentColor 14%, transparent);
    border-radius: 18px;
    background: color-mix(in srgb, currentColor 3%, transparent);
    box-shadow: 0 10px 26px color-mix(in srgb, currentColor 4%, transparent);
}
.fma-pub-result::before {
    content:'';
    position:absolute;
    top:0; left:22px; right:22px;
    height:2px;
    background: color-mix(in srgb, var(--primary-color, #4e9ce5) 62%, transparent);
    border-radius: 0 0 4px 4px;
}
.fma-pub-result-top { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:.5rem; }
.fma-pub-result-market { font-size: .74rem; font-weight: 750; text-transform: uppercase; letter-spacing:.055em; opacity:.78; }
.fma-pub-result-status {
    font-size: .63rem; letter-spacing:.065em; font-weight:800; text-transform: uppercase;
    border-radius: 20px;
    padding: .23rem .6rem;
    border: 1px solid color-mix(in srgb, currentColor 16%, transparent);
    background: color-mix(in srgb, currentColor 4%, transparent);
}
.fma-pub-result-status--forecast {
    border-color: color-mix(in srgb, var(--primary-color, #4e9ce5) 36%, transparent);
    background: color-mix(in srgb, var(--primary-color, #4e9ce5) 10%, transparent);
}
.fma-pub-result-direction {
    font: 800 clamp(1.3rem, 2vw, 1.75rem)/1.22 'Montserrat', 'Inter', system-ui, sans-serif;
    letter-spacing: -.037em;
    margin: 1.4rem 0 .4rem;
    overflow-wrap: anywhere;
}
.fma-pub-result-subtitle { font-size: .79rem; line-height: 1.6; opacity: .75; }
.fma-pub-result-footer { margin-top:1.3rem; padding-top:.7rem; display:flex; gap:.5rem; align-items:baseline; border-top:1px solid color-mix(in srgb, currentColor 10%, transparent); }
.fma-pub-weight { font: 800 1.1rem/1.2 'Montserrat', system-ui, sans-serif; }
.fma-pub-weight-label { font-size: .7rem; opacity:.65; }
.fma-pub-footnote { font-size: .74rem; line-height: 1.65; opacity: .67; margin: 1.05rem 0 1.9rem; }
@media (max-width: 900px) {
    .block-container { padding-inline: 1.1rem; }
    .fma-public-hero { padding: 1.4rem 1.25rem; }
    .fma-public-market-head { gap: .6rem; }
    .fma-pub-result { min-height: 170px; padding: 1.1rem; }
}
@media (prefers-reduced-motion: reduce) {
    .stButton > button, [data-testid="stFormSubmitButton"] > button { transition:none; }
}

/* =============================================================
   FMA_PUBLIC_P6 — themed cards, private-style navigation, compact inputs
   ============================================================= */
:root { --fma-accent: var(--primary-color, #58a6ff); }
[data-testid="stSidebar"] {
    border-right: 1px solid color-mix(in srgb, currentColor 12%, transparent);
}
[data-testid="stSidebarNav"] { padding: .22rem .65rem .75rem; }
[data-testid="stSidebarNav"] ul { gap: .18rem; }
[data-testid="stSidebarNav"] [data-testid="stSidebarNavItems"] { gap: 0; }
[data-testid="stSidebarNav"] a {
    border-radius: 11px !important;
    margin-block: .12rem;
    padding: .68rem .75rem !important;
    font-family: 'Inter', system-ui, sans-serif;
    font-weight: 550;
    transition: background .15s ease, box-shadow .15s ease;
}
[data-testid="stSidebarNav"] a:hover {
    background: color-mix(in srgb, var(--fma-accent) 8%, transparent);
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: color-mix(in srgb, var(--fma-accent) 14%, transparent) !important;
    box-shadow: inset 4px 0 0 var(--fma-accent), 0 4px 14px rgba(0,0,0,.08);
    font-weight: 750;
}
[data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"] {
    font-size: .76rem;
    letter-spacing: .03em;
    margin-top: 1rem;
}
.fma-public-kpis {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: .78rem;
    margin: .7rem 0 .7rem;
}
.fma-public-kpi {
    position: relative;
    min-width: 0;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, currentColor 11%, transparent);
    border-radius: 17px;
    background: color-mix(in srgb, currentColor 2.6%, transparent);
    padding: 1.05rem 1.12rem 1.1rem;
    box-shadow: 0 7px 19px rgba(0,0,0,.11), 0 1px 2px rgba(0,0,0,.035);
}
.fma-public-kpi::before {
    content: ''; position: absolute; top: 0; left: 19px; right: 19px; height: 2px;
    background: color-mix(in srgb, var(--fma-accent) 44%, transparent);
}
.fma-public-kpi-label {
    font: 650 .70rem/1.45 'Inter',system-ui,sans-serif;
    letter-spacing: .008em; opacity: .72;
    min-height: 1.1em;
}
.fma-public-kpi-value {
    font: 800 clamp(1.20rem, 2.1vw, 1.86rem)/1.2 'Montserrat','Inter',sans-serif;
    letter-spacing: -.045em;
    margin-top: .65rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}
.fma-public-kpi-foot { margin-top: .48rem; opacity: .61; font-size: .67rem; }
.fma-public-panel-title {
    font: 750 1.15rem/1.3 'Montserrat', 'Inter', system-ui, sans-serif;
    letter-spacing: -.025em;
    margin: 1.5rem 0 .45rem;
}
.fma-public-disclosure { font-size: .76rem; opacity: .70; line-height: 1.65; }
/* Keep the scientific controls unchanged while reducing their visual footprint. */
[data-testid="stForm"] {
    max-width: 940px;
    margin-inline: auto;
    border-radius: 18px;
}
[data-testid="stForm"] [data-testid="stVerticalBlockBorderWrapper"] {
    max-width: 940px;
    border-radius: 15px !important;
    padding: .10rem .16rem;
    box-shadow: 0 4px 15px rgba(0,0,0,.045);
}
[data-testid="stForm"] [data-testid="stNumberInput"] { max-width: 270px; }
[data-testid="stForm"] [data-testid="stNumberInput"] input {
    min-height: 39px !important;
    font-variant-numeric: tabular-nums;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: .91rem;
}
[data-testid="stForm"] [data-testid="stNumberInput"] [data-baseweb="input"] {
    border-radius: 11px !important;
    background: color-mix(in srgb, currentColor 2.5%, transparent);
}
[data-testid="stForm"] [data-testid="stNumberInput"] [data-baseweb="input"]:focus-within {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--fma-accent) 25%, transparent);
}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] > button {
    min-height: 2.85rem;
    border-radius: 12px;
    box-shadow: 0 5px 15px color-mix(in srgb, var(--fma-accent) 17%, transparent);
}
[data-testid="stDataFrame"] {
    overflow: hidden;
    border-radius: 14px;
    border: 1px solid color-mix(in srgb, currentColor 12%, transparent);
    box-shadow: 0 7px 17px rgba(0,0,0,.05);
}
@media (max-width: 1120px) {
    .fma-public-kpis { grid-template-columns: repeat(3, minmax(0,1fr)); }
}
@media (max-width: 690px) {
    .fma-public-kpis { grid-template-columns: repeat(2, minmax(0,1fr)); gap: .6rem; }
    .fma-public-kpi { padding: .85rem .8rem; }
    .fma-public-kpi-value { font-size: 1.24rem; }
    [data-testid="stForm"] [data-testid="stNumberInput"] { max-width: 100%; }
}

/* FMA_PUBLIC_P6_2 — centered single-column match picker */
.st-key-pub_match_picker_panel {
    width: 100%;
    max-width: 940px;
    margin-inline: auto;
}
.st-key-pub_match_picker_panel [data-testid="stSelectbox"],
.st-key-pub_match_picker_panel [data-testid="stTextInput"],
.st-key-pub_match_picker_panel [data-testid="stDateInput"] {
    width: 100%;
}
/* Competition is intentionally a little taller than the other controls. */
.st-key-pub_competition [data-baseweb="select"] > div {
    min-height: 3.2rem !important;
    align-items: center;
}
.st-key-pub_match_picker_panel [data-testid="stWidgetLabel"] {
    margin-bottom: .12rem;
}
@media (max-width: 940px) {
    .st-key-pub_match_picker_panel { max-width: 100%; }
}

</style>
"""


def apply_public_theme() -> None:
    """Inject Public-only visual tokens; leave theme choice to Streamlit."""
    st.markdown(PUBLIC_THEME_CSS, unsafe_allow_html=True)


def sidebar_brand() -> None:
    """Public-only brand; grouped active navigation is rendered by st.navigation."""
    st.sidebar.markdown(
        '<div class="fma-pub-sidebar">'
        '<div class="fma-pub-sidebar-mark">FM</div>'
        '<div class="fma-pub-sidebar-name">Football Market<br>Analytics</div>'
        '<div class="fma-pub-sidebar-label">PUBLIC EXPERIENCE</div>'
        '<div class="fma-pub-sidebar-rule"></div>'
        '</div>', unsafe_allow_html=True,
    )


def overview_kpi_cards(items: list[tuple[str, str, str]]) -> None:
    """Render purely presentational KPI tiles using already-computed tracker metrics."""
    cards = []
    for label, value, foot in items:
        cards.append(
            '<div class="fma-public-kpi">'
            f'<div class="fma-public-kpi-label">{html.escape(label)}</div>'
            f'<div class="fma-public-kpi-value">{html.escape(value)}</div>'
            f'<div class="fma-public-kpi-foot">{html.escape(foot)}</div>'
            '</div>'
        )
    st.markdown('<div class="fma-public-kpis">'+''.join(cards)+'</div>', unsafe_allow_html=True)


def page_hero(title: str, *, kicker: str, subtitle: str, status: str | None = None) -> None:
    status_html = f'<div class="fma-public-copy">{html.escape(status)}</div>' if status else ''
    st.markdown(
        '<section class="fma-public-hero">'
        f'<div class="fma-public-kicker">{html.escape(kicker)}</div>'
        f'<div class="fma-public-title">{html.escape(title)}</div>'
        f'<div class="fma-public-copy">{html.escape(subtitle)}</div>'
        '<div class="fma-pub-hero-pills">'
        '<span class="fma-pub-pill">Interactive model demo</span>'
        '<span class="fma-pub-pill">Asian Handicap + Asian Total</span>'
        '<span class="fma-pub-pill">Five European leagues</span>'
        '</div>'
        f'{status_html}'
        '</section>', unsafe_allow_html=True,
    )


def section_header(step: str, title: str, description: str = '') -> None:
    st.markdown(
        '<div class="fma-pub-section">'
        f'<span class="fma-pub-step">{html.escape(step)}</span>'
        '<div>'
        f'<div class="fma-pub-section-title">{html.escape(title)}</div>'
        f'<div class="fma-pub-section-copy">{html.escape(description)}</div>'
        '</div><span class="fma-pub-section-line"></span></div>',
        unsafe_allow_html=True,
    )


def market_card_header(title: str, subtitle: str, *, badge: str, kind: str = 'neutral') -> None:
    # No dynamic style code; `kind` is maintained for compatibility only.
    st.markdown(
        '<div class="fma-public-market-head">'
        f'<span class="fma-public-badge">{html.escape(badge)}</span>'
        '<div>'
        f'<div class="fma-public-market-title">{html.escape(title)}</div>'
        f'<div class="fma-public-market-subtitle">{html.escape(subtitle)}</div>'
        '</div></div>', unsafe_allow_html=True,
    )


def selected_match(home: str, away: str, competition: str, match_date: str) -> None:
    st.markdown(
        '<div class="fma-pub-match-strip">'
        '<div><div class="fma-pub-match-label">Selected fixture</div>'
        f'<div class="fma-pub-match-teams">{html.escape(home)} <span style="opacity:.48">vs</span> {html.escape(away)}</div></div>'
        f'<div class="fma-pub-match-meta">{html.escape(competition)} &nbsp;·&nbsp; {html.escape(match_date)}</div>'
        '</div>', unsafe_allow_html=True,
    )


def forecast_card(market: str, line: str, label: str, context: str,
                  *, status: str, weight: float | None) -> None:
    shown_status = {'FORECAST': 'Model forecast', 'NO_SIGNAL': 'No signal'}.get(status, 'Unavailable')
    status_style = '--forecast' if status == 'FORECAST' else ''
    weight_markup = ''
    if weight is not None:
        weight_markup = (
            '<div class="fma-pub-result-footer">'
            f'<span class="fma-pub-weight">{weight:g}u</span>'
            '<span class="fma-pub-weight-label">Public V2 strategy stake · not a betting recommendation</span>'
            '</div>'
        )
    st.markdown(
        '<section class="fma-pub-result">'
        '<div class="fma-pub-result-top">'
        f'<span class="fma-pub-result-market">{html.escape(market)} · {html.escape(line)}</span>'
        f'<span class="fma-pub-result-status fma-pub-result-status{status_style}">{shown_status}</span>'
        '</div>'
        f'<div class="fma-pub-result-direction">{html.escape(label)}</div>'
        f'<div class="fma-pub-result-subtitle">{html.escape(context)}</div>'
        f'{weight_markup}'
        '</section>', unsafe_allow_html=True,
    )
