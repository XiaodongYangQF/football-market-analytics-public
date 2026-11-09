# P8.1C-2 — Scientific Runtime Identity and Mac-to-Linux Parity

**Status:** The diagnostic code and tests are implemented. Actual Mac baselines and independent Linux parity verification must be established separately; the public scientific prediction service has **not** been enabled.

## Delivered tools

- `scripts/build_private_parity_cases.py`: derives genuine P7 worker inputs from a pre-existing **private analysis-export ZIP**, preserving AH, main OU and fixed-2.5 quote inputs, fixture identity and date. It does not publish private data or rerun science during extraction.
- `scripts/verify_scientific_runtime.py`: `preflight`, `baseline` and `verify` modes for scientific dependency checks, genuine Mac P7 output collection and same-input Linux comparison.
- `fma_portfolio/runtime_parity.py`: scientific source SHA-256, explicitly declared read-only reference-data hashes, Python/dependency identity and per-case timing, plus strict AH/OU result comparison.
- Fail-closed restrictions preventing private case corpora, baselines and reports from being written inside the public repository.

No Private science, Local Public port 8502, or frozen Public V2 AH/OU rule is changed.

## Original installation

With the earlier P8.1C-1 patch installed, stop port 8504 and run:

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C2_Scientific_Runtime_Parity_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

Use these existing local directories for the original Mac setup:

```text
Private project: $HOME/Projects/football_market_analytics_v2_2
Science root:    $HOME/Projects/football_market_analytics
Data root:       $HOME/Projects/football_market_analytics
```

Use the original scientific interpreter, when necessary, through `--model-python` or a private `FMA_PORTFOLIO_MODEL_PYTHON` environment variable; the UI interpreter is not a guaranteed substitute.

## Extract private same-input cases (Mac)

```bash
mkdir -p "$HOME/Documents/fma-private-parity"
chmod 700 "$HOME/Documents/fma-private-parity"
python scripts/build_private_parity_cases.py \
  --analysis-export "$HOME/Downloads/FMA_Analysis_Export_20261108_220349.zip" \
  --output "$HOME/Documents/fma-private-parity/cases.json" \
  --count 40
```

The example source archive originally supplied 40 distinct historical inputs, eight per league across five competitions. These are **historical parity test inputs**, not a prospective pre-kickoff forecast release. If a private cases file already exists, validate and reuse it rather than overwriting it.

## Preflight and genuine Mac baseline

```bash
python scripts/verify_scientific_runtime.py preflight \
  --project-root "$HOME/Projects/football_market_analytics_v2_2" \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics"
```

The original non-resumable baseline command is:

```bash
python scripts/verify_scientific_runtime.py baseline \
  --project-root "$HOME/Projects/football_market_analytics_v2_2" \
  --science-root "$HOME/Projects/football_market_analytics" \
  --data-root "$HOME/Projects/football_market_analytics" \
  --cases "$HOME/Documents/fma-private-parity/cases.json" \
  --baseline-file "$HOME/Documents/fma-private-parity/mac_baseline.json"
```

For safer checkpointed execution with the finalized season gate, prefer [P8_1C2E_ELIGIBILITY_GATE.md](P8_1C2E_ELIGIBILITY_GATE.md). A real failed worker or missing scientific environment must be investigated rather than marked successful. Output files are owner-only and not silently overwritten.

### Reference data identity

By default, the tool may report `REFERENCE COVERAGE: NOT_CAPTURED`; a source-code hash alone is insufficient for production readiness. Discover the actual scientific read-only reference-data dependencies, declare the same ordered `--reference-root /absolute/path` arguments on Mac and Linux, and confirm that the declared set genuinely covers the required data. A hash of an irrelevant folder does not satisfy this requirement.

## Independent private Linux verification

Only on an approved, isolated Linux host, transfer the independently licensed frozen worker/science runtime and required read-only reference assets through an authorized **private** channel. Do not copy the Mac home directory, database, private `.env`, odds ledger or secrets. Place private cases/baseline outside the GitHub checkout with restrictive permissions.

Example **illustrative** Linux paths (not an assertion those folders already exist):

```bash
python scripts/verify_scientific_runtime.py verify \
  --project-root /srv/fma/private-project \
  --science-root /srv/fma/science \
  --data-root /srv/fma/data \
  --model-python /srv/fma/science-venv/bin/python \
  --reference-root /srv/fma/approved-reference-data \
  --cases /srv/fma/private-evidence/cases.json \
  --baseline-file /srv/fma/private-evidence/mac_baseline_with_refs.json \
  --report-file /srv/fma/private-evidence/linux_parity_report.json
```

## Acceptance criteria

- **PARITY PASS:** actual predictions equal Mac baseline results under the tool's strict comparison; source and explicitly declared reference hashes agree; per-case runtime limits are met. This alone may still reflect insufficient reference coverage or Mac-only testing.
- **PROMOTION-CANDIDATE GATE PASS:** additionally covers at least 20 cases over at least three leagues, AH/OU forecasts and genuine `NO SIGNAL` outcomes, a macOS baseline vs Linux verifier, compatible Python/dependency versions and matching explicitly declared reference hashes.
- **Production launch:** requires further assurance of complete reference-data coverage, licensing, memory/concurrency limits, read-only deployment, isolation, identity management, network controls and recovery procedures.

Failures such as `scientific_source=False`, `declared_reference_data=False`, `PARITY FAIL`, `coverage_gate=INCOMPLETE`, or `scientific_dependency_versions_equal=False` must be investigated, not bypassed.

The Mac/Linux track is independent of P8.1D daily performance and P8.1E GitHub pre-match receipts; it does not rewrite profit, historical forecasts or trading decisions.
