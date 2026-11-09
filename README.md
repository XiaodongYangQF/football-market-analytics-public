# Football Market Analytics

### Public quantitative research portfolio · Hosted research dashboard

**[Live Streamlit app](https://football-market-analytics.streamlit.app/)** · **[GitHub repository](https://github.com/XiaodongYangQF/football-market-analytics-public)** · **[Public pre-match receipt Issues](https://github.com/XiaodongYangQF/football-market-analytics-public/issues)**

**Public landing page:** `Performance overview` (historical simulated performance). The separate `Pre-match archive` remains empty until genuinely prospective receipts are published. **Hosted interactive forecasts are not enabled** until the private scientific backend passes independent deployment controls. The public website does not access the owner's Mac or Private model.

Operations: [Public launch / README handoff (中文)](P8_2D_PUBLIC_LAUNCH_CN.md) · [First genuine pre-match receipt acceptance (中文)](P8_2E_FIRST_RECEIPT_ACCEPTANCE_CN.md).

Football Market Analytics combines **historical AH/OU performance evaluation** with the real **P7.4 prematch input workflow** in one Streamlit interface. It preserves the distinction between (a) a public GitHub repository with no scientific engine and (b) an **owner-local Mac preview** that can invoke the pre-existing, frozen P7 prediction worker from a separate Private installation.

> **Hosting limitation:** The interactive forecast form is included in the publicly reviewable application. **Actual new forecasts are disabled on hosted/public instances** until a secured, license-reviewed scientific execution service has passed Linux, parity, authentication and concurrency gates. We neither fabricate predictions nor silently substitute a simpler model.

## What visitors can see

- **Interactive forecast:** P7.4 input workflow — select/enter a match, enter home Asian Handicap line and two odds, main Asian Total line and two odds, and Fixed 2.5 Over/Under reference odds. The fixed line is a calibration input, *not* a third public signal. Host mode clearly indicates execution is unavailable.
- **Research & performance:** simulated P&L, ROI, AH vs OU comparison, historical ledger and downloadable public-only records.
- **Saved forecasts:** in an owner-local preview, generate a real forecast through P7's existing frozen science worker. A forecast is saved to **browser session** only after clicking **Save forecast**. Export or restore an official P7.4-compatible JSON backup; these personal snapshots **never enter official ROI**.
- **No auto-recording:** Changing a selected fixture clears the unsaved preview; selecting a fixture or typing market data never creates an official prediction.

## Initial Public V2 evaluation snapshot

| Measure | Published V2 dataset |
| :-- | --: |
| Settled signals | **34** (24 distinct fixtures) |
| Simulated net P&L | **+3.8000u** |
| Simulated turnover | **34.0u** |
| Weighted ROI | **+11.18%** |
| AH, 17 settled | −0.3875u (−2.28%) |
| OU, 17 settled | +4.1875u (+24.63%) |
| Additional rows | 31 NO SIGNAL, 2 NOT_RECORDED |

*Recorded settlement, **not** actual money won.* The observation window is short; correlated AH/OU wagers, exploratory OU execution quotes and unnormalized source dates limit inference. Never interpret 11.18% as a stable or prospective ROI.

## Run the unified Portfolio, public-safe mode

Create a Python **3.11** environment (Conda recommended on Mac; do not use the old Python 3.8 base):

```bash
conda create -n fma-portfolio python=3.11 pip -y
conda activate fma-portfolio
python -m pip install -r requirements-dev.txt
python scripts/security_check.py
python -m pytest -q
python -m streamlit run app.py --server.port=8504 --server.address=127.0.0.1
```

The two application modules run in the same UI. **Real prediction remains disabled** in this mode (deliberate). Historical performance continues working.

## Owner-local: run the EXISTING frozen P7 model

On the owner's Mac, after verifying the original Private project and its external scientific/reference directories are present:

```bash
conda activate fma-portfolio
python scripts/run_owner_local.py --check
python scripts/run_owner_local.py --port 8504
```

This launcher reads **only** `FMA_SCIENCE_ROOT` and `FMA_DATA_ROOT` from the existing project's local `.env` when available; otherwise provide `--science-root` and `--data-root`. It **forces bind address 127.0.0.1**, isolates each child execution, and executes the **existing P7.2 `model_worker.py` from your separate Private project**. It does not copy the model, Private references or internal rules into the repository. If the scientific runtime needs its preinstalled Python 3.11 environment, you may set `FMA_PORTFOLIO_MODEL_PYTHON` to that Python's absolute path in the *local terminal only*. Do not set owner-local environment variables in a public/cloud deployment.

The bridge uses the genuine frozen P7 worker with a **strict AH/OU result allowlist**; any absent model or unsafe response fails closed. The runner's existence check is **not evidence of real parity**; verify an actual unchanged input against Local Public before accepting the installation.

For full Mac instructions see [INSTALL_CN.md](INSTALL_CN.md).

## What is intentionally NOT included

No Private model equations, science executors, reference data, account history, private rules, Anchor paths, secrets, betting access or third-party fixture database are included. `data/fixtures.csv` is deliberately header-only, awaiting a reviewed/publicly licensed fixture feed. In **owner-local mode only**, the interface reads the **existing P7 Public** file `deployment/public_web/data/fixtures.csv` from the owner's separate project, **without copying or publishing it**. The cloud-hosted interface still has no bundled fixtures; visitors can enter matches manually. The public code contains only UI, input checks, a validated P7 forecast-archive contract, evaluation, settlement and a local-only adapter interface.

The **public instance never reads** the original Private folder; a local-owner subprocess accesses it only after an explicit loopback launch. The independent original Private and Local Public versions are not modified by this repository.

## Repository layout

```text
app.py                              Unified Streamlit Portfolio
fma_portfolio/metrics.py             Evaluation/aggregation
fma_portfolio/settlement.py          Independent Asian quarter-line settlement checks
fma_portfolio/release.py             Strict public V2 allowlisted data export
fma_portfolio/p7/forecast_ui.py      Curated real P7.4 input and saved-forecast page
fma_portfolio/p7/forecast_contract.py P7 request validation without model code
fma_portfolio/p7/saved_forecasts.py   Public session archive validation/export
fma_portfolio/p7/fixtures_store.py   Safe fixture import and manual-mode support
fma_portfolio/p7/fixture_source.py  Owner-local external P7 Public schedule selection
fma_portfolio/p7/owner_local.py      Mac-only P7 worker bridge (disabled by default)
scripts/run_owner_local.py           Owner Mac loopback-only launch
scripts/security_check.py           Publication safety scanning
scripts/build_public_release.py      Manual refresh from Local Public snapshot
data/public_v2.json                 Frozen public performance snapshot
data/fixtures.csv                  Header-only empty fixture list (licensing gate)
scripts/check_owner_fixtures.py     Read-only local fixture diagnostic
docs/                               Evaluation protocol and cloud deployment gates
tests/                              Public-only reproducibility and boundary tests
```

## Deployment roadmap

- **P8.1A complete:** historical Public V2 portfolio.
- **P8.1B complete in source:** integrated P7.4 form and local owner-only real-model bridge, no real scientific parity claimed outside the Mac.
- **P8.1C pending:** hardened, authenticated prediction backend, deployable scientific assets, repeatable Mac/Linux parity, licensing, resource and concurrency audits. Until then cloud host can serve the performance pages and preview the forecast form, **not execute actual predictions**.
- **P8.2:** link the public portfolio and, once approved, prediction service from the personal website.

### Privacy and research integrity

The Public V2 rules and 1u settlement policy are not altered by this integration. The source data represent historical *pre-match quotes*, even when an archived record was processed later. Distinguish repeatable historical replays from predictions available to bettors before kickoff. Simulated returns are descriptive; probability calibration and forward-market benchmarks remain part of future research.

Maintained for research portfolio use by GitHub [@XiaodongYangQF](https://github.com/XiaodongYangQF). No betting recommendation, financial guarantee, or live-trade execution. No source/data reuse rights are granted unless a license is separately supplied.

## Daily performance publishing (P8.1D)

The repository never syncs directly with Private. Updates follow **Private → Local Public (existing manual publication) → curated JSON → this public repository**. A complete snapshot is regenerated each time rather than adding daily profits by hand. This maintains a single audited P&L computation and supports corrected or newly settled events under review.

```bash
# From the public Portfolio repo, with fma-portfolio Conda environment active:
bash scripts/publish_daily_performance.sh --dry-run
bash scripts/publish_daily_performance.sh --apply
# Once the repository is already on GitHub, and the data diff is reviewed:
bash scripts/publish_daily_performance.sh --push
```

`--dry-run` is the default. `--apply` writes **only** `data/public_v2.json` and `data/public_release_manifest.json`. `--push` also runs validation and requires an explicit `PUBLISH` confirmation; it stages only those two public data files and refuses an unexpected remote, missing history, modified archived signals, or silent settled-result corrections. Never pass a Private-ledger path to the publisher. See [release workflow](docs/release_process.md).

The initial 34-settled, +3.80u example above is a **historical baseline**, not a live claim about the latest GitHub commit. The current deployment's Performance overview reads `data/public_v2.json` and recomputes all metrics directly.

For future public timestamp evidence of genuinely pre-kickoff signals, see the separate [prematch publication proposal](docs/prematch_receipts.md). An ordinary daily result refresh is **not** itself proof that a forecast was publicly posted before kickoff.


## P8.1E — public pre-match GitHub receipt archive

The `Pre-match archive` tab is a **separate** prospective evidence track. Owner-local P7.4 JSON exports can be published in explicitly selected same-kickoff batches by `scripts/publish_prematch_receipt.py`. Each real `--publish` creates a public GitHub Issue with the complete quote inputs/model results first (server-created timestamp); it then commits a SHA-256-checked JSON mirror for portfolio browsing. Ordinary site visitors cannot execute the private model.

This is not immutable notarization, independent bookmaker verification, or evidence of a real bet. User-provided kickoff times remain unverified. The independent P8.1D settlement ledger is not double-counted. See `P8_1E_PREMATCH_RECEIPTS_CN.md` and `docs/prematch_receipts.md`.


## P8.1C-1 — Authenticated hosted prediction pilot (NOT publicly live)

The public UI retains the original 8504 loopback-only scientific bridge. A separate,
disabled-by-default **hosted model client** and a **localhost-only protected
gateway** now implement the server-to-server AH/OU contract. Hosted inference
requires an OIDC authenticated, email-allowlisted user, HTTPS ingress and an
independently hosted, private frozen scientific runtime. It does **not** grant
anonymous visitors access to the owner's Mac or enable online predictions on GitHub.

Read [P8.1C 中文交接](P8_1C_HOSTED_PILOT_CN.md) and
[hosted prediction security guide](docs/hosted_prediction.md) before testing.
Do not store tokens, scientific models, private paths, fixtures or raw odds in GitHub.
P8.1D daily updates and P8.1E pre-match receipts remain unchanged.

### P8.1C-2 — Scientific runtime parity tools (pre-deployment)

The Mac→Linux parity workflow is available in `scripts/build_private_parity_cases.py`
& `scripts/verify_scientific_runtime.py`. It builds a **private** historical
input corpus from existing analysis snapshots, fingerprints frozen code and
explicitly selected reference-data files, computes actual Mac P7 worker
outputs, then checks exact output equality on a separate Linux runtime.
Private input corpora and baselines must never enter GitHub. This feature
**does not** ship private models or expose a prediction service to the public.
See [`P8_1C2_SCIENTIFIC_PARITY_CN.md`](P8_1C2_SCIENTIFIC_PARITY_CN.md) and
[`docs/linux_runtime_migration.md`](docs/linux_runtime_migration.md).

## P8.1C-2E — Season-aware eligibility gate

The 2026–27 five-league public roster/promotion policy lives in
`data/eligibility_policy_2026_27.json`. Owner-local UI, prediction API and new
prematch receipt publishing fail closed for current-season promoted clubs,
unknown teams and unverified seasons. **INELIGIBLE is not NO SIGNAL.**
For a resumable Mac parity baseline that preserves original checkpoint indices
and records excluded cases separately, follow [P8_1C2E_ELIGIBILITY_GATE_CN.md](P8_1C2E_ELIGIBILITY_GATE_CN.md).
No frozen model implementation, performance rule, historic public release or
private scientific source files are included or changed by this gate.
