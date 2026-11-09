# P8.1C-2E — 2026–27 Season Eligibility Gate

## Scope and terminology

This policy changes only the independent public Portfolio. It does **not** change Private science, Local Public port 8502, the Public V2 trading policy or historical P&L.

| Status | Meaning |
|---|---|
| `ELIGIBLE` | Team identity and season membership were verified; the team is not newly promoted in the specified 2026–27 policy. This does not imply a forecast signal. |
| `INELIGIBLE` | Current-season promoted club excluded by policy. Do not invoke P1/P2; **not** equivalent to `NO SIGNAL`. |
| `UNVERIFIED` | Unknown team, out-of-policy season, incompatible identity or missing configuration; reject conservatively. |
| `NO SIGNAL` | A legitimate model outcome **only after** the eligible model was executed successfully. |

The five-league 2026–27 roster and documented source URLs are stored in `data/eligibility_policy_2026_27.json`. Team identifiers use canonical Local Public names with explicitly configured public display aliases. No fixture lists, betting odds or private data are included.

Within the original 40-case real-input sample, case 24 (Lazio–Monza) and case 32 (Freiburg–Schalke 04) were excluded as promoted-team fixtures; the remaining 38 passed the eligibility gate. A prior successful worker response for case 24 means earlier case-32 worker failure cannot simply be attributed to promotion status.

## Original Mac patch installation

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C2E_Season_Eligibility_Gate_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

## Check eligibility before executing science

```bash
python scripts/eligible_mac_baseline.py \
  --cases "$HOME/Documents/fma-private-parity/cases.json" \
  --plan-only
```

The original sample target is `40 total; 38 eligible; 2 ineligible; 0 unverified`, with cases 24 and 32 excluded. This read-only plan must not overwrite the source cases or checkpoints.

## Reuse qualifying checkpoints and build the Mac baseline

```bash
python scripts/eligible_mac_baseline.py \
  --project-root "$HOME/Projects/football_market_analytics_v2_2" \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics" \
  --cases "$HOME/Documents/fma-private-parity/cases.json" \
  --checkpoint-dir "$HOME/Documents/fma-private-parity/mac_checkpoints" \
  --eligible-cases-file "$HOME/Documents/fma-private-parity/eligible_cases.json" \
  --coverage-file "$HOME/Documents/fma-private-parity/eligibility_coverage.json" \
  --baseline-file "$HOME/Documents/fma-private-parity/mac_baseline_eligible.json" \
  --max-case-seconds 120
```

Original case indices (1–40) are retained. Eligible successful checkpoints are reused only after input/source/runtime identity checks; excluded cases are not executed. A new genuine worker error stops further execution without deleting previously accepted checkpoints. The script does not silently overwrite any existing output file.

The three resulting files must remain **outside GitHub**: `eligible_cases.json` (38 eligible inputs); `eligibility_coverage.json` (source and policy hashes, exclusions, counts); and `mac_baseline_eligible.json` (real Mac outputs, **not** Linux parity).

For Linux verification, use the same private `eligible_cases.json` and Mac baseline, and provide `--eligibility-coverage-file`. The verifier checks the policy SHA-256 before considering `PROMOTION-CANDIDATE GATE: PASS`. Missing or mismatched coverage fails the gate even when individual outputs match. `REFERENCE COVERAGE: NOT_CAPTURED` still blocks production readiness without an audited reference-data inventory.

Owner-local UI, forecast API, gateway and new GitHub pre-match receipt publication all perform eligibility validation. Existing historic Public V2 records and Issues are not silently edited, deleted or retroactively reclassified.
