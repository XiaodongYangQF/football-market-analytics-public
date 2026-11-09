"""P8.2D: public-safe landing page and links (no Streamlit import required)."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_public_navigation_starts_with_performance_not_prediction():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(app)
    radio_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                   and isinstance(node.func, ast.Attribute) and node.func.attr == "radio"
                   and node.args and isinstance(node.args[0], ast.Constant)
                   and node.args[0].value == "Explore"]
    assert len(radio_calls) == 1
    pages = ast.literal_eval(radio_calls[0].args[1])
    assert pages == ["Performance overview", "Pre-match archive", "Forecast ledger",
                     "Methodology & limits", "Interactive forecast"]
    assert "forecast_page()" in app  # owner-local bridge is preserved
    assert 'if page == "Pre-match archive"' in app


def test_live_url_and_evidence_caveat_in_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://football-market-analytics.streamlit.app/" in readme
    assert "https://github.com/XiaodongYangQF/football-market-analytics-public/issues" in readme
    assert "Hosted interactive forecasts are not enabled" in readme
    assert "genuinely prospective" in readme


def test_app_displays_source_link_without_private_access():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Source code & public record history" in app
    for banned in ("from backend", "from core", "import backend", "PRIVATE_API_KEY"):
        assert banned not in app
