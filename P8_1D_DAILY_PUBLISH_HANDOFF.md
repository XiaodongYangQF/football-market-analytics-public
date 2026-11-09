# P8.1D — Daily Public Performance Publishing Pipeline

## Scope

- Read only the **already published Local Public** `../football_market_analytics_v2_2/public_data/tracker_snapshot.json`, never the Private ledger or scientific model.
- Allowlist `POST_ACTIVATION_V2` primary-market AH/OU records into `data/public_v2.json`.
- Recalculate settled signal counts, simulated net P&L and ROI, and independently validate AH/OU settlement.
- Fail closed on missing previously published predictions or unnoticed changes to historical line, direction, price or settlement. Allow and disclose a valid transition from a `NO SIGNAL` placeholder to a recorded same-fixture forecast.
- Write `data/public_release_manifest.json` containing SHA-256 hashes of the input snapshot and public records, aggregate metrics and processing timestamp, excluding private source paths and model details.
- Default to read-only dry run. `--apply` only changes two public JSON files; `--push` requires repository validation and explicit `PUBLISH` confirmation and stages only those files.

## Original patch installation

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1D_Daily_Public_Pipeline_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

## Daily routine

First perform the existing Private → Local Public (8502) publication of analysis and results. Do not point this script at `runtime_data`.

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio

bash scripts/publish_daily_performance.sh --dry-run
bash scripts/publish_daily_performance.sh --apply
bash scripts/publish_daily_performance.sh --push
```

Before `--push`, verify that a public GitHub repository exists and the code changes have already been separately reviewed and committed. If the source has not been published, review and use `scripts/publish_github.sh` first. A no-change run does not manufacture new profit: the first manifest records a publication processing event, not a pre-kickoff timestamp.

**Separate evidence:** GitHub Issues for pre-match receipts are managed by P8.1E; daily Git updates do not retroactively prove a forecast existed publicly before kickoff. See [docs/prematch_receipts.md](docs/prematch_receipts.md).
