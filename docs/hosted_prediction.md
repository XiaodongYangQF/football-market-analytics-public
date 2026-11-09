# P8.1C-1 — Hosted forecast contract / authenticated pilot

**Not yet a publicly accessible model service.** Code is staged so that a separately operated private model executor can eventually answer the GitHub Public Streamlit UI without copying Private scientific code to GitHub.

## System boundary

```text
Visitor browser → Streamlit UI [GitHub Public code]
                          │
               OIDC authenticated & email allowlisted
                          │   server-side secret; HTTPS only
                          ▼
              Secured HTTPS ingress [NOT built here]
                  │ independent access / rate limits
                  ▼
          Loopback gateway 127.0.0.1:8765
           strict JSON + bearer token + global quota
                  │   one worker at a time
                  ▼
            Existing frozen P7 model_worker.py
                  │  isolated subprocess/temp sandbox
                  ▼
             AH/OU projection ONLY
```

The loopback gateway is an integration *component*, not a substitute for a reverse proxy, Internet firewall, private server deployment or OIDC authentication. **Never forward its TCP port directly to the Internet.** Do not commit environment secrets, scientific bundles or live fixture/odds data.

## Invariants

- `FMA_HOSTED_FORECAST_ENABLED` defaults off, and the server-side Streamlit user must be logged in via OIDC, with their email in `FMA_HOSTED_ALLOWED_EMAILS`. No anonymous inference.
- `FMA_HOSTED_FORECAST_API_URL` must be a trusted HTTPS **origin**, not a user input. `FMA_HOSTED_ALLOW_LOOPBACK_HTTP=1` is for local pilot requests to `http://127.0.0.1` only. Delete it before any hosted deployment.
- `FMA_HOSTED_FORECAST_API_TOKEN` is a strong shared secret stored outside the repo. Token is never sent to browsers or the P7 child process; client connects only from the server process.
- Gateway binds `127.0.0.1` only, uses fixed `/v1/forecast`, checks bearer authorization *before* reading request content, strictly validates the same P7 contract, accepts at most 4 KB input, returns at most 4 KB output, strips errors, limits one active model run and defaults to four runs per hour with 30 sec cool-down. Counters reset on restart: production needs persistent edge quotas.
- Response has ONLY `ah` and `ou`: status, direction and 1.0u stake. No model internals or artifacts. Fixed 2.5 is a calibration input, not an extra output.
- Forecasts from hosted pilot are session-only until explicitly exported and handled by P8.1E. They do **not** automatically enter Performance; no funds traded.
- Public GitHub source continues to omit the actual frozen models and private data.

## Local-only model bridge pilot (owner Mac)

A. With your real scientific environment active, run the preflight:

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/run_private_forecast_gateway.py --check \
 --project-root "$HOME/Projects/football_market_analytics_v2_2" \
 --science-root "$HOME/Projects/football_market_analytics" \
 --data-root "$HOME/Projects/football_market_analytics"
```

B. If a private scientific interpreter differs from `fma-portfolio`, set `FMA_PORTFOLIO_MODEL_PYTHON` to the absolute path. Generate a strong shared secret in your **private terminal** and export it without writing it in repo or shell command history:

```bash
export FMA_GATEWAY_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python scripts/run_private_forecast_gateway.py \
 --project-root "$HOME/Projects/football_market_analytics_v2_2" \
 --science-root "$HOME/Projects/football_market_analytics" \
 --data-root "$HOME/Projects/football_market_analytics" \
 --port 8765
```

This starts a **loopback-only** HTTP service. Keep the terminal open. In a *second terminal*, use the exact same token from a secure out-of-band location; do not print it or paste it into public files. Test credentials and a request file under `~/Documents` (outside the GitHub repository). For example:

```bash
export FMA_HOSTED_FORECAST_ENABLED=1
export FMA_HOSTED_FORECAST_API_URL=http://127.0.0.1:8765
export FMA_HOSTED_ALLOW_LOOPBACK_HTTP=1
export FMA_HOSTED_ALLOWED_EMAILS=owner@example.com
export FMA_HOSTED_FORECAST_API_TOKEN='<same-secret-token>'
python scripts/check_hosted_prediction.py --request "$HOME/Documents/fma_pilot_request.json"
```

**Placeholder email above is NOT a real login configuration.** This CLI only verifies protocol/transport. It does not assert an OIDC login or compare the original vs remote engine; Streamlit hosted UI requires correctly configured OIDC and its own deployed server-side secret. To compare an actual frozen P7 local run with the gateway using the same JSON inputs, run `python scripts/check_gateway_parity.py --request "$HOME/Documents/fma_pilot_request.json" --science-root "$HOME/Projects/football_market_analytics" --data-root "$HOME/Projects/football_market_analytics"` with the Gateway still running. This runs the real model **twice**; check strict equality, then repeat using diverse already recorded cases. Neither the illustrative team names nor a test stub demonstrates scientific parity.

Example input JSON *for format only*, not a forecast or an actual fixture (store outside the repo):

```json
{
  "league": "E0", "home": "Example Home", "away": "Example Away", "fixture_date": "2026-11-21",
  "ah_line": -0.25, "ah_home_odds": 1.94, "ah_away_odds": 1.94,
  "asian_line": 2.5, "asian_over_odds": 1.92, "asian_under_odds": 1.94,
  "fixed_over_odds": 1.92, "fixed_under_odds": 1.94
}
```

## Requirements BEFORE Internet hosting

1. Deploy a **separate** permission-reviewed scientific runtime on a secure server. Do not depend on a powered-on personal Mac or expose a tunnel into its private directories.
2. Reproduce multiple saved identical-input forecasts in the Linux runtime; freeze hashes and versions. Validate model run time/memory and nested imports.
3. Configure Streamlit OIDC with an email allowlist for the pilot, plus secure HTTPS ingress to the gateway and secret delivery. Authenticate/limit requests at the *edge* independently; never simply expose local port 8765.
4. Enforce durable global budgets (per-account and per-IP), request quotas, workload queueing, worker process limits, systemd/docker containment and infrastructure monitoring. Gateway's in-memory counters are defense in depth only.
5. Review third-party odds/fixture data licensing and public output terms.
6. Only after successful pilot, separately design/approve an **anonymous visitor** access policy. Removing the OIDC gate without compensating controls is out of scope.

## Relationship to earlier stages

- P8.1D performance ingestion and P8.1E GitHub Issue pre-match receipts remain unchanged.
- The user still has to publish a record via P8.1E for prospective evidence. A model response by itself is not a public pre-match receipt.
- Private and existing Local Public remain unmodified.
