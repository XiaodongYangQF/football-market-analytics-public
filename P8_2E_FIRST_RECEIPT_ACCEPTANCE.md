# P8.2E — First Genuine Pre-match GitHub Receipt: Acceptance Checklist

**Status:** No real prospective issue was created during the original dry-run acceptance. Do not treat historical or post-kickoff model replays as public pre-kickoff publications. Private and Local Public trading rules remain frozen.

## 0. Read-only GitHub prerequisites

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
git status -sb
gh auth status
gh api repos/XiaodongYangQF/football-market-analytics-public \
  --jq '{private,has_issues,default_branch,archived}'
```

Expected repo fields: `private=false`, `has_issues=true`, `default_branch=main`, `archived=false`. The working tree must have no unrelated/uncommitted changes when running the real publisher. Enable Issues only after explicit operator approval if needed.

## 1. Select an eligible fixture that has not kicked off

- Verify the **actual UTC kickoff**, competition and home/away identities using a credible current schedule. A fixture date alone cannot determine the kickoff clock time.
- Current-season promoted clubs and unverifiable identities are `INELIGIBLE` or `UNVERIFIED`, never `NO SIGNAL`.
- A single Issue batch must contain only fixtures with the **same exact kickoff time**.
- Reserve enough time to compute the frozen forecast, review all inputs and complete the GitHub Issue and mirror push. The Mac saved time does not replace the GitHub server timestamp.

## 2. Export a compatible public prediction record

In owner-local 8504, complete the real model workflow, click `Save forecast`, then `Backup / export (JSON)` and retain the P7.4 file privately. Alternatively, after Private → Local Public publication, use the [P8.2F Local Public bridge](P8_2F_LOCAL_PUBLIC_RECEIPT_BRIDGE.md) and its verified public-only feed. Do **not** upload Private analysis ZIPs, model logs or parity files.

## 3. Inspect available records, read-only

```bash
ARCHIVE="$HOME/Downloads/fma_saved_forecasts.json"
python - "$ARCHIVE" <<'PYCODE'
from pathlib import Path
import sys
from fma_portfolio.p7.saved_forecasts import parse_archive
for row in parse_archive(Path(sys.argv[1]).read_bytes()):
    print(row['record_id'], row['fixture_date'], row['competition'],
          row['home_team'], 'vs', row['away_team'], row['saved_at_utc'])
PYCODE
```

Choose explicit `--record-id` values; never select an entire archive without verifying every fixture and kickoff.

## 4. Dry run before live publication

This is a **template**, not an assertion of a scheduled match:

```bash
python scripts/publish_prematch_receipt.py \
  --archive "$ARCHIVE" \
  --record-id "ACTUAL_RECORD_UUID" \
  --kickoff-utc "YYYY-MM-DDTHH:MM:SSZ" \
  --kickoff-basis "Official fixture schedule, manually verified" \
  --quote-source "Actual bookmaker and timestamp, if independently recorded"
```

Inspect printed teams, AH/OU lines, both prices, fixed 2.5 calibration odds, public strategy directions, saved timestamp and batch identity. No Issue or commit is created by a dry run. Never invent a bookmaker identity or quote-capture time.

## 5. Publish only when all details are verified

Repeat exactly the reviewed command with `--publish`. The operator must type `PUBLISH` in the terminal. The publisher creates a public Issue first, records GitHub API `created_at`, and then pushes the SHA-256-linked JSON mirror.

Successful acceptance requires: `ON_TIME_DECLARED` relative to a **correctly verified, user-declared** kickoff; accurate Issue body and matching mirror hash; and a visible receipt with Issue link in the Streamlit `Pre-match archive`. This is **not** independent validation of the fixture clock or executable bookmaker odds.

If Issue creation succeeds but the mirror push fails, do not create a duplicate Issue. Recover the existing mirror/commit using `--resume-issue <number>` or the documented recovery procedure in [docs/prematch_receipts.md](docs/prematch_receipts.md).

## 6. Settle after the match

Continue the established P8.1D Local Public → Portfolio settlement routine. Original Issue content is never overwritten with the match result. Receipt-to-ledger linking remains strict; unmatched receipts remain `UNLINKED` and do not create synthetic P&L.

## Research integrity

- A GitHub Issue can be edited/deleted. Hashes, mirrors and commit history improve inspectability, not immutability.
- GitHub API `created_at` is authoritative for its creation event; local Mac clock and Git author date are not.
- Retrospective forecasts based on historical prematch quotes must not enter the prospective cohort.
- `INELIGIBLE`, `NO SIGNAL` and worker failure are separate statuses.
- Future visitor-requested forecasts must not automatically enter the official strategy track record.
