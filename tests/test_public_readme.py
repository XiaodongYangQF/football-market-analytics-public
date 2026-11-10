"""Guard public reader-facing claims and links in the project README."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_readme_has_live_demo_and_real_screenshot():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://football-market-analytics.streamlit.app/" in readme
    assert "assets/dashboard-overview.png" in readme
    assert (ROOT / "assets" / "dashboard-overview.png").is_file()

def test_readme_distinguishes_private_parametric_inference_and_live_returns():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    for phrase in (
        "poisson-equivalent", "parametric", "research directions", "private p1/p2",
        "out-of-sample probability calibration", "nonparametrically",
        "retrospective", "simulated", "hosted public instance", "not verified live-trading",
    ):
        assert phrase in readme

def test_technical_reference_preserved():
    ref = (ROOT / "docs" / "maintainer_reference.md").read_text(encoding="utf-8")
    assert "Daily performance publishing" in ref
    assert "P8.1E" in ref
    assert "P8.2F" in ref
