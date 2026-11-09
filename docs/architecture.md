# Architecture and security boundary

This portfolio is a standalone and stateless Streamlit app. It imports only the public `fma_portfolio` package, the curated local JSON dataset, Pandas and Plotly. There is no network connection to the Private backend, no shared runtime data, no external model path, and no write path in the UI.

```text
                    Local research environment (NOT GitHub)
       ┌──────────────────────────────────────────────────┐
       │ Private core / stored pre-match cases / ledgers │
       └───────────────────────┬──────────────────────────┘
                               │ protected local publication
       ┌───────────────────────▼──────────────────────────┐
       │ Local Public snapshot (read-only export source) │
       └───────────────────────┬──────────────────────────┘
                               │ manual, allowlisted transformation
                               ▼
                       data/public_v2.json
                               │
                      fma_portfolio/metrics.py
                               │
                           app.py
                               │
                  GitHub readers / public dashboard
```

## Exposure safeguards

- A new sibling repository: never `git init` the Private project folder.
- Default `*.env`, secrets, runtime data, internal backups, log files and SQLite stores are excluded.
- `sanitize_snapshot` constructs an **allowlisted public object** field-by-field rather than copying arbitrary source keys.
- Source Private policy IDs, rule IDs, analysis IDs, case references and trade IDs are omitted even though some may be present in internal snapshots.
- No public code imports the original `backend`, `core` or private `app` directories.
- `scripts/security_check.py` and CI reject unexpected data keys, dangerous paths, and common credential patterns before release.

A source-code audit or secret detector cannot guarantee that every publication decision is appropriate. Manually review the staged Git diff before pushing data to a public repository.

## P8.1B integration boundary (9 November 2026)

The repository now includes the curated P7.4 forecast interface as `fma_portfolio/p7/forecast_ui.py`, with public-only request validation and browser-session archives. It does **not** carry the scientific worker, frozen rule evaluator, model reference assets or Private project source. On the owner's Mac, `scripts/run_owner_local.py` binds 127.0.0.1 only and invokes the worker from the **separate** existing `football_market_analytics_v2_2` directory via a bounded child process and allowlisted environment. No new forecasts are available in cloud/hosted mode. Read `docs/cloud_prediction_gates.md` before attempting that later phase.
