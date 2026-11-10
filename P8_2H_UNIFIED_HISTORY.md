# P8.2H — Unified Historical Performance Dashboard

## What changes

The public dashboard now shows one combined historical research record, without
separate headline panels for earlier research and later recorded V2. The data
assets remain separate so that methodology, settlement and prospective receipt
claims cannot be conflated.

- Public V2 rules: reverse AH-A and OU-B, preserve AH-B/AH-C/OU-A.
- Historical evidence: `data/historical_replay.json`, 68 settled 1u AH/main-line
  OU signals on 48 archived fixtures, fully reconciled against generic quarter-line
  settlement and the stored opposing-side odds.
- Existing Local Public V2: `data/public_v2.json`, 34 settled signals in its
  initial 67-row snapshot on 33 tracked fixtures.
- Unified initial output: **81 tracked fixtures, 102 settled signals,
  102u stake, +22.9125u simulated P&L, +22.46% stake-weighted ROI**.
- By market: AH 46 settled, +9.0625u, +19.70%; OU 56 settled,
  +13.8500u, +24.73%.
- Fixture ledger: searchable, status-filterable, sortable and paginated,
  including result score, 1X2, AH/OU predictions and settlement details.

**Research integrity:** This is a mixed retrospective/recorded historical
simulation and is not an independently pre-kickoff-published series. The
combined ROI must never be described as fully prospective or a live betting
return. The separate GitHub Issues receipt tab remains the prospective track.

## Installation

1. Apply the patch ZIP to the **Portfolio repository only**:

   ```bash
   cd "$HOME/Projects"
   unzip -o "$HOME/Downloads/FMA_P8_2H_Unified_History_Dashboard_Patch_20261109.zip" -d "$HOME/Projects"
   cd "$HOME/Projects/football-market-analytics-public"
   conda activate fma-portfolio
   ```

2. Run quality and integrity checks:

   ```bash
   python scripts/check_public_english.py
   python scripts/security_check.py
   python -m pytest -q
   ```

3. Review **only** these changed/new files before staging:

   ```bash
   GIT_PAGER=cat git status --short
   GIT_PAGER=cat git diff -- app.py README.md docs/methodology.md scripts/security_check.py
   ```

   Stage **only**:

   ```bash
   git add -- app.py README.md docs/methodology.md scripts/security_check.py \
     data/historical_replay.json fma_portfolio/unified_history.py \
     tests/test_unified_history.py P8_2H_UNIFIED_HISTORY.md
   GIT_PAGER=cat git diff --cached --name-status
   git diff --cached --check
   ```

4. When the tests pass and the staged files match this scope:

   ```bash
   git commit -m "portfolio: add unified historical performance and fixture table"
   git push origin main
   ```

5. Open the hosted site and inspect **Performance overview**, then
   **Forecast ledger**. The ordinary daily release script remains unchanged:

   ```bash
   bash scripts/publish_daily_performance.sh --dry-run
   ```

   Its `--apply` still writes **only** `data/public_v2.json` and the normal
   manifest. It never regenerates or stages `data/historical_replay.json`.

## Dataset boundary and policy

The 68 historical rows come from archived earlier-period research, not the
separately audited 56-fixture OU comparison (which includes a partly overlapping
weekend corpus). This ensures that published V2 quotes are not replaced by
an alternative weekend research quote or silently conflated. The public
fixture count includes NO SIGNAL and NOT_RECORDED cases; the simulated ROI
only counts verified settled 1u signals. A market missing entirely from an
archived fixture is shown as missing (`—`), never falsely classified as
NO SIGNAL.

All source payloads and code are English-only and contain no Private engine,
internal IDs or user/device paths. A public data release cannot prove the
historical quote was executable, or that forecasts were publicly available
before kickoff.
