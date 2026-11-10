"""P8.2I visual-only sidebar regression checks.

These deliberately inspect the app source instead of depending on Streamlit's
browser DOM, which changes between Streamlit releases.
"""
from pathlib import Path
import ast
import re

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _sidebar_source():
    start = APP.index("with st.sidebar:")
    end = APP.index("\nrows = [r for r in all_rows", start)
    return APP[start:end]


def test_sidebar_groups_and_accessible_brand():
    sidebar = _sidebar_source()
    assert 'class="fma-side-brand"' in sidebar
    assert 'aria-label' not in sidebar or 'aria-hidden="true"' in sidebar
    assert 'class="fma-side-section fma-side-section--first">Research' in sidebar
    for section in ("Filters", "Public data", "Links"):
        assert f">{section}</div>" in sidebar
    assert 'class="fma-side-snapshot"' in sidebar


def test_navigation_order_and_multiselects_remain_native():
    sidebar = _sidebar_source()
    pages = (
        "Performance overview", "Pre-match archive", "Forecast ledger",
        "Methodology & limits", "Interactive forecast",
    )
    assert all(page in sidebar for page in pages)
    assert all(sidebar.index(pages[i]) < sidebar.index(pages[i + 1]) for i in range(4))
    assert 'page = st.radio(' in sidebar
    assert 'markets = st.multiselect("Market", ["AH", "OU"], default=["AH", "OU"])' in sidebar
    assert 'selected_leagues = st.multiselect("Competition", leagues, default=leagues)' in sidebar
    assert 'if page != "Interactive forecast":' in sidebar
    assert 'markets = ["AH", "OU"]' in sidebar


def test_active_style_scoped_to_sidebar_and_keeps_keyboard_focus():
    assert '[data-testid="stSidebar"] [data-testid="stRadio"]' in APP
    assert 'label:has(input:checked)' in APP
    assert 'label:focus-within' in APP
    assert 'box-shadow: inset 3px 0 0 #52d6ca;' in APP
    assert '/* Keep the native radio input and labels:' in APP


def test_filter_css_is_scoped_and_no_public_numeric_claims_added():
    css = APP.split('st.markdown("""<style>', 1)[1].split('</style>""",', 1)[0]
    assert '[data-testid="stSidebar"] [data-testid="stMultiSelect"]' in css
    assert '[data-testid="stSidebar"] [data-baseweb="tag"]' in css
    sidebar = _sidebar_source()
    assert 'Simulated results' in sidebar
    assert 'Not verified live trading' in sidebar
    assert not re.search(r'\b\d+(?:\.\d+)?%\b', sidebar)


def test_public_links_are_static_and_safe():
    sidebar = _sidebar_source()
    assert 'https://github.com/XiaodongYangQF/football-market-analytics-public"' in sidebar
    assert 'https://github.com/XiaodongYangQF/football-market-analytics-public/issues"' in sidebar
    assert sidebar.count('rel="noopener noreferrer"') == 2
    assert not re.search(r'[\u3400-\u9fff]', sidebar)


def test_python_syntax_and_page_body_not_duplicated():
    ast.parse(APP)
    assert APP.count('with st.sidebar:') == 1
    assert APP.count('elif page == "Performance overview":') == 1
    assert APP.count('elif page == "Forecast ledger":') == 1
    assert APP.count('if page == "Interactive forecast":') == 1
