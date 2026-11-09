# Football Market Analytics — Mac Installation and Operational Guide

## Architecture and security boundaries

This GitHub repository is an **independent public Portfolio**. Do not overwrite `football_market_analytics_v2_2` or modify the frozen Private science, Local Public (port 8502) strategy, or historic Public V2 evaluation results.

The hosted Portfolio provides Performance overview, Pre-match archive, Forecast ledger, Methodology and an Interactive forecast form. **Real prediction execution is disabled in the cloud.** Only an explicitly launched, loopback-bound **owner-local** version on the owner's Mac may invoke the separately installed P7 frozen worker. Do not expose that owner-local process through a public tunnel.

## Install or update the Portfolio

For a **fresh** Python environment use Python 3.11 rather than the earlier Python 3.8 `base` environment:

```bash
conda create -n fma-portfolio python=3.11 pip -y
conda activate fma-portfolio
cd "$HOME/Projects/football-market-analytics-public"
python -m pip install -r requirements-dev.txt
python scripts/security_check.py
python -m pytest -q
python -m pip check
```

For historical installations from a patch ZIP, stop port 8504 first; inspect the patch's exact filenames and back up any uncommitted work before extracting it to `$HOME/Projects`. Never publish local virtual environments, `.env`, private model resources, or personal archives.

## Start hosted-safe preview (no real prediction)

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python -m streamlit run app.py --server.address=127.0.0.1 --server.port=8504
```

Open `http://127.0.0.1:8504`. Model execution is intentionally unavailable in this mode. An incomplete hosted fixture list is not an error: the public `data/fixtures.csv` remains header-only for licensing reasons.

## Start owner-local real-model preview

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/run_owner_local.py --check \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics"
python scripts/run_owner_local.py --port 8504 \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics"
```

The launcher can also obtain `FMA_SCIENCE_ROOT` and `FMA_DATA_ROOT` from the separate Private project's local `.env` when available. If the frozen worker needs its original Python interpreter, set `FMA_PORTFOLIO_MODEL_PYTHON` locally to the absolute interpreter path, **never in GitHub**. The owner-local server binds strictly to `127.0.0.1`.

Compare at least one identical full-market input (AH line and both prices; main OU line and both prices; fixed 2.5 reference prices) between the owner-local Portfolio and existing Local Public before claiming same-model output compatibility. A successful file-path preflight alone does not establish numerical parity.

## Original P8.1B owner-local schedule fix

Owner-local mode reads the existing P7 Local Public fixture CSV read-only. To check it:

```bash
python scripts/check_owner_fixtures.py \
  --project-root "$HOME/Projects/football_market_analytics_v2_2"
```

The hosted app never accesses this local file, and the repository deliberately does not bundle the original third-party fixture list. See [P8_1B_SCHEDULE_FIX.md](P8_1B_SCHEDULE_FIX.md).

## Daily public performance synchronization

First publish through the existing Private → Local Public process, then:

```bash
cd "$HOME/Projects/football-market-analytics-public"
bash scripts/publish_daily_performance.sh --dry-run
bash scripts/publish_daily_performance.sh --apply
bash scripts/publish_daily_performance.sh --push
```

`--push` requires the explicit `PUBLISH` confirmation. It stages only the approved public data and manifest files. **A daily Git commit is not evidence of pre-kickoff public prediction publication.**

## Prospective forecast receipts

Use the separate [P8.2E first-receipt acceptance procedure](P8_2E_FIRST_RECEIPT_ACCEPTANCE.md) for genuinely prospective forecasts. To avoid double entry, the [P8.2F bridge](P8_2F_LOCAL_PUBLIC_RECEIPT_BRIDGE.md) exports already confirmed Private → Local Public signals to the existing GitHub Issue receipt protocol. These are separate from daily settlement and remain dry-run until explicit approval.

## Public deployment

After source, data licensing, security scans and test results are reviewed, publish only allowlisted files to GitHub. The original `scripts/publish_github.sh` can initialize a repository; use normal reviewed Git commits for later source updates. Hosted scientific execution needs the separate authenticated, isolated P8.1C runtime gates and independent Mac/Linux parity acceptance before enablement.
