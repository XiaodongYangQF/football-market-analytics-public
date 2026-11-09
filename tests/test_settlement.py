import json
from pathlib import Path

import pytest

from fma_portfolio.settlement import settle, verify_saved_record

ROWS = json.loads((Path(__file__).resolve().parents[1]/"data"/"public_v2.json").read_text())["records"]


def test_all_settled_public_entries_independently_reconcile():
    records = [r for r in ROWS if r["state"] == "SETTLED"]
    bad = [r["record"] for r in records if not verify_saved_record(r)]
    assert len(records) > 0
    assert bad == []


@pytest.mark.parametrize("args,expected", [
    (("AH", "HOME", -0.75, 1.875, "2–1"), ("HALF_WIN", 0.4375)),
    (("AH", "AWAY", +0.25, 1.9, "0–0"), ("HALF_WIN", 0.45)),
    (("AH", "AWAY", -0.25, 1.9, "2–2"), ("HALF_LOSS", -0.5)),
    (("AH", "HOME", -1.0, 2.0, "2–1"), ("PUSH", 0)),
    (("OU", "OVER", 2.25, 2.0, "2–0"), ("HALF_LOSS", -0.5)),
    (("OU", "UNDER", 2.25, 2.0, "1–1"), ("HALF_WIN", 0.5)),
    (("OU", "OVER", 3.0, 2.0, "2–1"), ("PUSH", 0)),
    (("OU", "UNDER", 3.0, 2.0, "4–0"), ("LOSS", -1)),
])
def test_quarter_and_whole_line_cases(args, expected):
    assert settle(*args) == expected


def test_non_quarter_line_rejected():
    with pytest.raises(ValueError):
        settle("AH", "HOME", -0.37, 2.0, "1–0")
