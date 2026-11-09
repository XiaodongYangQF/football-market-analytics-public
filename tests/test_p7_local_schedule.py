"""P8.1B owner-local fixture source: use the existing P7 *Public* schedule only."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from fma_portfolio.p7.fixture_source import fixture_source
from fma_portfolio.p7.fixtures_store import load_fixtures, fixture_options, team_options


HEADERS = (
    'league', 'fixture_date', 'home_team', 'away_team',
    'canonical_home_team', 'canonical_away_team'
)


def create_public_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerow({
            'league': 'SP1', 'fixture_date': '2026-11-22',
            'home_team': 'Atlético Madrid', 'away_team': 'Barcelona',
            'canonical_home_team': 'Ath Madrid',
            'canonical_away_team': 'Barcelona',
        })
        writer.writerow({
            'league': 'E0', 'fixture_date': '2026-11-21',
            'home_team': 'Leeds', 'away_team': 'Tottenham',
            'canonical_home_team': 'Leeds', 'canonical_away_team': 'Tottenham',
        })


def test_hosted_mode_never_loads_owner_private_project(monkeypatch, tmp_path):
    src = tmp_path / 'owner_project'
    create_public_fixture(src / 'deployment/public_web/data/fixtures.csv')
    path, local = fixture_source(Path('data/fixtures.csv'), owner_local=False, project_root=str(src))
    assert path == Path('data/fixtures.csv')
    assert local is False


def test_owner_mode_reads_local_p7_public_fixtures(monkeypatch, tmp_path):
    original = tmp_path / 'owner_project'
    local_file = original / 'deployment/public_web/data/fixtures.csv'
    create_public_fixture(local_file)
    source, local = fixture_source(Path('data/fixtures.csv'), owner_local=True,
                                   project_root=str(original))
    assert local is True
    assert source == local_file
    rows = load_fixtures(source, 'SP1')
    assert len(rows) == 1
    assert rows[0]['canonical_home'] == 'Ath Madrid'
    assert fixture_options(rows, 'Upcoming', date(2026, 11, 9)) == rows
    assert ('Atlético Madrid', 'Ath Madrid') in team_options(rows)


def test_owner_mode_without_original_schedule_falls_back_to_safe_empty(monkeypatch, tmp_path):
    published = Path(__file__).resolve().parents[1] / 'data' / 'fixtures.csv'
    path, local = fixture_source(published, owner_local=True, project_root=str(tmp_path))
    assert local is False
    assert path == published
    assert load_fixtures(path, 'SP1') == []


def test_owner_mode_without_root_uses_public_snapshot(monkeypatch):
    path, local = fixture_source(Path('data/fixtures.csv'), owner_local=True, project_root=None)
    assert path == Path('data/fixtures.csv')
    assert local is False


def test_schedule_source_never_refers_to_runtime_data():
    import fma_portfolio.p7.fixture_source as source_module
    text = Path(source_module.__file__).read_text(encoding='utf-8')
    assert "'deployment' / 'public_web'" in text
    assert "'runtime_data'" not in text
    assert "'ledgers'" not in text


def test_schedule_diagnostic_reads_existing_public_schedule(tmp_path):
    from scripts.check_owner_fixtures import main
    create_public_fixture(tmp_path / 'deployment/public_web/data/fixtures.csv')
    assert main(['--project-root', str(tmp_path)]) == 0


def test_schedule_diagnostic_missing_file_is_rejected(tmp_path):
    from scripts.check_owner_fixtures import main
    assert main(['--project-root', str(tmp_path)]) == 2
