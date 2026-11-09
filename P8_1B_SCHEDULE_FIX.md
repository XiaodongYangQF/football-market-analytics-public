# P8.1B — Owner-local Fixture Selection Fix (2026-11-09)

## Symptom and cause

The 8504 `Interactive forecast` page could display `0 fixtures shown · 0 in league` for La Liga or another competition because the public GitHub template intentionally ships only the CSV header in `data/fixtures.csv`.

## Implemented behavior

Only in loopback-bound owner-local mode, `scripts/run_owner_local.py` loads the original Local Public file **read-only** from:

```text
$HOME/Projects/football_market_analytics_v2_2/deployment/public_web/data/fixtures.csv
```

It preserves the canonical team mapping without copying the underlying third-party schedule into the public repository. Cloud-hosted prediction execution and fixture access remain disabled.

## Original Mac patch installation

Stop port 8504 with `Ctrl+C`, then:

```bash
cd "$HOME/Projects/football-market-analytics-public"
mkdir -p "$HOME/fma_patch_backups/p8_1b_schedule"
cp -p fma_portfolio/p7/forecast_ui.py "$HOME/fma_patch_backups/p8_1b_schedule/"
unzip -o "$HOME/Downloads/FMA_P8_1B_Local_Schedule_Hotfix_20261109.zip" -d "$HOME/Projects"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
python scripts/check_owner_fixtures.py \
  --project-root "$HOME/Projects/football_market_analytics_v2_2"
```

An earlier source export contained approximately 1,751 fixtures across five leagues; the owner's actual local file is authoritative. If the diagnostic cannot locate it, inspect the original project instead of fabricating a fixtures file.

Start owner-local mode:

```bash
python scripts/run_owner_local.py \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics" \
  --port 8504
```

Open `http://127.0.0.1:8504`, select `Interactive forecast → La Liga → Upcoming` or `All`, and check fixture choices.

**Boundaries:** This patch changes no Private science, Local Public 8502, V2 trading strategy or model output. Correct fixture display is not evidence that the deployed model produces scientifically identical forecasts; compare same-input AH/OU output separately.
