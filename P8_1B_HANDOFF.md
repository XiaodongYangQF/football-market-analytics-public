# P8.1B — Integrated P7.4 Forecast and Public V2 Portfolio

## Delivered

- Added **Interactive forecast** to the existing Portfolio app while retaining Performance overview, Forecast ledger, and methodology pages.
- Preserved the P7.4 input contract: home AH line and both odds; main Asian Total line and both odds; fixed 2.5 Over/Under reference odds. Only **AH and OU** are public prediction markets.
- Reused the existing P7 public forecast and `NO SIGNAL` contract, including the 1-unit Public V2 policy. Neither Private nor Local Public frozen rules were changed.
- Predictions enter the browser-session archive **only after Save forecast**. CSV and JSON backup/export and JSON restore are supported; saved session forecasts are not added to official P&L.
- Changing fixtures clears an unsaved prediction preview.
- The scientific worker remains outside GitHub. Only the owner's loopback-bound Mac instance can execute the existing P7 `model_worker.py` through `scripts/run_owner_local.py`. Hosted forecast execution remains disabled.
- The initial Public V2 snapshot (34 settled records, +3.80u, +11.18% simulated ROI) was unchanged. There is no direct connection to the Private or Local Public ledger.
- The public `data/fixtures.csv` is header-only until third-party fixture rights have been reviewed; manual match entry remains possible.

## Original delivery validation

At initial P8.1B delivery, 42 tests and the security scan passed, and Python compilation succeeded. That test environment did not include an actual Mac scientific runtime or a Streamlit browser session, so those checks were not claimed as complete end-to-end model validation. Later milestones have their own acceptance results.

## Installation and follow-up

See [INSTALL.md](INSTALL.md) for Mac setup, ordinary hosted-safe startup, and the owner-local model runner. Verify real same-input results against Local Public before relying on scientific parity. `scripts/publish_github.sh` handles initial repository publication after security review; a live hosted scientific service requires the separate P8.1C security gates.
