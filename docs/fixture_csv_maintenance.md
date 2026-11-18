# P8 — Offline Hosted Fixture CSV Maintenance

## Scope

The existing Official Public Streamlit app reads the six-column, reviewed
`data/fixtures.csv` from this GitHub repository. This fixture-selection data is
**not** the scientific Current Data used by the Private AH/OU model. Updating
this file does not run the model, revise frozen rules, or settle old forecasts.

The public file contains only these fields:

`league,fixture_date,home_team,away_team,canonical_home_team,canonical_away_team`

Do not publish private model inputs, strengths, Anchors, bookmaker odds, credentials,
internal run logs, or extra columns. Public match facts do not automatically grant
permission to republish a third-party compiled fixture database: verify the
source's license/terms and permission to redistribute before each publication.

## First-time migration

The reviewed six-column schedule is generated from an authorized source by
`FMA_P8_Offline_Fixtures_v2/install_offline_fixtures.py` (distributed separately,
not committed to this repository). The source may be the existing owner-local
P7 Public fixture CSV **only when redistribution rights have been established**.
The installer backs up affected files outside the public repository and removes
the hosted fixture API dependency.

## Future updates

When the approved source's fixture dates or pairings change, use the separate
`FMA_P8_Offline_Fixtures_v2/refresh_public_fixtures.py` utility on the owner's
Mac. Dry-run first, inspect the source and date/league counts, and apply only
after confirming publication rights. The utility backs up the previous CSV.

Then, in the **existing** `football-market-analytics-public` checkout:

```bash
conda activate fma-portfolio
cd "$HOME/Projects/football-market-analytics-public"
python -m pytest -q
python scripts/security_check.py
python scripts/check_public_english.py
git diff --check
git diff -- data/fixtures.csv
```

Only after review and successful checks:

```bash
git add data/fixtures.csv
git diff --cached --stat
git commit -m "P8: refresh approved public fixtures"
git push
```

Streamlit Community Cloud updates the **existing** app from the tracked `main`
branch. There is no need to create a new Streamlit deployment. The published
file is a curated snapshot, not a live fixture service. Verify the fixture
picker on each league after the update.

## Public/Private boundary

The Owner-Local preview may use the existing local P7 Public schedule instead
of this published CSV, preserving its original team-name mappings. Official
Public reads the published snapshot and exposes only permitted fixture fields.
Hosted real model inference remains separately disabled until its protected
execution service is enabled and independently validated.

The old `FMA_FIXTURE_API_TOKEN` setting is unused after this migration and may
be deleted from Streamlit Secrets after the offline site is verified.
