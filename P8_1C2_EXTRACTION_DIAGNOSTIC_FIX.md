# P8.1C-2 — Private Parity-Case Extraction Diagnostics

This update improves the explanation of `STOPPED: private analysis extraction could not complete safely.` It does **not** relax safety checks, overwrite private files, or alter the scientific engine, prediction rules, Private, or Local Public.

## Original patch installation

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1C2_Extraction_Diagnostic_Hotfix_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python -m pytest -q
python scripts/security_check.py
```

The original patch reported 96 tests passing and `SECURITY CHECK PASS`. This is an historical patch-specific count, not the current repository-wide count.

## Diagnose missing input or output files

```bash
ls -lh "$HOME/Downloads/FMA_Analysis_Export_20261108_220349.zip"
ls -lh "$HOME/Documents/fma-private-parity/cases.json"
```

Then extract if a valid private case file does not already exist:

```bash
python scripts/build_private_parity_cases.py \
  --analysis-export "$HOME/Downloads/FMA_Analysis_Export_20261108_220349.zip" \
  --output "$HOME/Documents/fma-private-parity/cases.json" \
  --count 40
```

Possible stop reasons:

| Diagnostic | Action |
|---|---|
| `SOURCE_MISSING` | Locate the actual export ZIP and correct `--analysis-export`. |
| `OUTPUT_EXISTS` | Validate and reuse `cases.json`; do not remove existing evidence. |
| `OUTPUT_PARENT_MISSING` | Create the approved private parent folder. |
| `SOURCE_NOT_ZIP` | Supply a valid ZIP archive. |
| `NO_VALID_SNAPSHOTS` | Review whether the export contains supported Private analysis snapshots. |
| `PERMISSION_DENIED` / `IO_ERROR` | Review filesystem permissions and storage availability. |

To validate an existing file without changing it:

```bash
python - <<'PYCODE'
from pathlib import Path
from fma_portfolio.runtime_parity import load_cases
p = Path.home() / 'Documents/fma-private-parity/cases.json'
rows = load_cases(p)
print('EXISTING CASES VALID:', len(rows))
print('LEAGUE COUNTS:', {k: sum(r['request']['league'] == k for r in rows)
                         for k in ('E0','D1','SP1','I1','F1')})
PYCODE
```

An expected fully sampled set contains 40 fixtures, eight per league. Retain all extracted cases outside the public repo (for example under `~/Documents/fma-private-parity`). Never paste the raw private dataset into an issue, commit, or troubleshooting message; share only diagnostic codes.
