# P8.1C-1 — Protected Hosted Forecast Pilot (Not Publicly Enabled)

## Implemented components

1. An isolated execution helper wraps the **existing P7.4 scientific worker** without modifying its inputs, AH/OU signals, settlement or policy.
2. `scripts/run_private_forecast_gateway.py` is loopback-only (`127.0.0.1:8765`) with bearer-token authentication, strict request/response allowlists, one worker at a time and conservative per-user request intervals. It must **not** be directly exposed to the Internet.
3. `fma_portfolio/hosted_client.py` provides disabled-by-default server-side HTTPS access for an independently hosted gateway. The Streamlit user must be OIDC-authenticated and email-allowlisted. All secrets remain server-side and outside GitHub.
4. `Interactive forecast` distinguishes owner-local 8504, explicitly approved hosted pilot users, and ordinary hosted visitors with real forecast execution disabled.
5. P8.1D daily P&L and P8.1E GitHub pre-match receipts remain independent; private computations never silently become public track-record evidence.

## Install the original patch on Mac

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C_Hosted_Prediction_Pilot_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

Check the existing owner-local instance:

```bash
python scripts/run_owner_local.py --check \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics"
```

Check the independent gateway's local prerequisites without running inference or opening external network access:

```bash
python scripts/run_private_forecast_gateway.py --check \
  --project-root "$HOME/Projects/football_market_analytics_v2_2" \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics"
```

A `GATEWAY PREFLIGHT PASS` means local paths and interpreter checks passed; it does **not** prove actual scientific parity or authorize public deployment.

## Optional isolated local API trial

Follow [docs/hosted_prediction.md](docs/hosted_prediction.md) to set `FMA_GATEWAY_TOKEN` in a private local environment, call `/v1/forecast` from a trusted client, and compare the output to the frozen worker using `scripts/check_gateway_parity.py` and an approved private request file. Repeat across competitions, AH/OU outcomes and genuine `NO SIGNAL` cases. Only strict same-input results can support deployment progression.

## Deployment blockers

A Linux-ready frozen scientific runtime, verified model dependencies and reference-data licensing; independent network security with HTTPS and authentication; real OIDC checks; request throttling, persistence/recovery, load/concurrency tests; and a policy for public access and bookmaker quote rights. **This pilot has not enabled real predictions for anonymous Internet visitors.**
