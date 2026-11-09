# P8.1C-2B — Resumable Mac Scientific Baseline

## Why an earlier run stopped after approximately 5 minutes 52 seconds

The original `verify_scientific_runtime.py baseline` imposed a per-case `--max-case-seconds 300` timeout but did not save progress after each case. A timeout, worker contract error, or another exception could stop an entire run without retaining completed cases. The elapsed time was consistent with a 300-second timeout on an individual case, but it did not prove that this was the cause.

This update adds per-case START/PASS/FAILED status messages and owner-only checkpoints. On a restart it revalidates input hashes, scientific-source identity and runtime identity before reusing successful checkpoints. The original script, frozen worker, rules and Local Public are untouched.

## Original installation

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C2_Resumable_Mac_Baseline_Hotfix_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python -m pytest -q tests/test_resumable_mac_baseline.py
python scripts/security_check.py
```

## Run the existing 40-case dataset

```bash
python scripts/resumable_mac_baseline.py \
  --project-root "$HOME/Projects/football_market_analytics_v2_2" \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics" \
  --cases "$HOME/Documents/fma-private-parity/cases.json" \
  --baseline-file "$HOME/Documents/fma-private-parity/mac_baseline.json" \
  --checkpoint-dir "$HOME/Documents/fma-private-parity/mac_checkpoints" \
  --max-case-seconds 120
```

- `CASE i/40: PASS`: that case succeeded and its private checkpoint was written.
- `FAILED (CASE_TIMEOUT)`: a case timed out; successful earlier checkpoints remain.
- `FAILED (WORKER_FAILURE)`: the frozen worker reported a failure, which requires separate diagnosis and does not itself establish a prediction discrepancy.
- `CHECKPOINT REUSED`: the previous case is reused after identity checks.
- Increase `--max-case-seconds` to 300 if justified. Do not delete previous checkpoints or overwrite an already complete baseline.

All cases, checkpoints and baselines must remain outside GitHub. This is diagnostic tooling, **not** model performance improvement or Linux parity. `REFERENCE COVERAGE: NOT_CAPTURED` remains a blocker for production-ready reference-data assurance.
