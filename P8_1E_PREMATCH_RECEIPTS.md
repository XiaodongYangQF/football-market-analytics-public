# P8.1E — GitHub Pre-match Forecast Receipts

## Purpose and evidence limitations

- A **GitHub Issue** is the first public publication event for a batch of genuinely pre-kickoff P7.4 forecasts. Each batch must contain fixtures with the **same actual UTC kickoff**. The Issue includes approved public AH/OU and fixed-2.5 quote inputs, final AH/OU forecast outcomes or `NO SIGNAL`, policy identifier and a user-declared kickoff.
- A JSON mirror in `data/forecast_receipts/` enables Portfolio browsing. SHA-256 checks link the Issue contents and local mirror.
- **Daily Performance** is still published separately via P8.1D. A new receipt does not automatically add an extra wager or payout to ROI.
- Personal X posts are optional curated sharing, not the primary timestamp authority.
- Neither Private/Local Public science nor owner-local 8504 model connectivity is changed. Hosted model execution remains disabled.

**Evidence standard:** GitHub API `created_at` records when the platform created the Issue. The kickoff is supplied by the operator and is **not** independently verified by this tool; bookmaker availability or real execution is not attested. Issues may be edited or deleted. This is publicly inspectable evidence, **not immutable notarization or a third-party audit**.

## Original installation

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_1E_GitHub_Prematch_Receipt_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

At initial P8.1E delivery the standalone patch had 73 automated tests passing. That is an historical count, not the current cumulative count. Before the first real publication, review and commit the code to the public repository so the `main` checkout is clean and synchronized with `origin/main`. The publisher intentionally refuses to bundle uncommitted source changes with forecast data.

## 1. Save a real prospective forecast

The original owner-local P7.4 workflow requires the operator to click `Save forecast` and `Backup / export (JSON)` before publication. The JSON must conform to the public P7.4 archive contract, for example `~/Downloads/fma_saved_forecasts.json`; a single CSV row is insufficient. After the P8.2F bridge, a verified Local Public feed may supply the same compatible format without double entry: [P8_2F_LOCAL_PUBLIC_RECEIPT_BRIDGE.md](P8_2F_LOCAL_PUBLIC_RECEIPT_BRIDGE.md).

Do not publish historical replays as if they were pre-kickoff predictions. Do not upload entire Private analysis ZIPs, runtime logs, scientific references, case corpora or private notebooks.

## 2. Read-only dry run

The following is a **CLI-format example only**, not a verified match or actual kickoff. Replace all match details and the UTC time from a trustworthy fixture schedule:

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/publish_prematch_receipt.py \
  --archive "$HOME/Downloads/fma_saved_forecasts.json" \
  --fixture-date 2026-11-14 \
  --competition "Bundesliga" \
  --saved-after "2026-11-14T14:00:00Z" \
  --kickoff-utc "2026-11-14T14:30:00Z"
```

A backup can contain predictions for many dates and kickoff times. Prefer one or more exact `--record-id UUID` selectors to avoid accidental inclusion; `--saved-after` alone does not verify kickoff alignment. Review **every** proposed fixture, market, quote and model outcome. Dry run creates neither an Issue nor a Git commit.

## 3. Publish only after explicit review

After a successful dry run, repeat the **same** command with `--publish` appended. The program validates the strict public JSON schema, eligible team/season policy, uniqueness, local saved timestamps, GitHub remote identity, clean/synchronized `main`, and public Issues capability. It shows the intended disclosure and requires the operator to enter `PUBLISH`.

The publisher then:

1. Creates a public GitHub Issue first and captures its platform `created_at`.
2. Compares this server timestamp with the **user-declared** UTC kickoff, reporting `ON_TIME_DECLARED` or `LATE_PUBLICATION`.
3. Creates a SHA-256-checked JSON mirror and pushes only that receipt file to GitHub `main`.
4. Prints the Issue URL, server timestamp, declared kickoff and mirror location.

Allow a practical buffer (initially at least 10–15 minutes) for data checks, model computation, network operations and operator review. An Issue first created after kickoff is a late release even if the forecast was generated on the Mac earlier.

### Recovery and verification

If Issue creation succeeds but Git push fails, **do not create a second Issue**. Preserve the existing Issue and recover its mirror using the existing commit/push or `--resume-issue <number>` procedure. Confirm the Issue body, mirror hash and GitHub `created_at` after recovery.

```bash
python scripts/verify_forecast_receipts.py
python scripts/security_check.py
python -m pytest -q
```

The receipt verifier compares currently accessible GitHub Issue content against its mirror. It cannot rule out every historical edit-and-restore or future deletion.

## 4. Post-match settlement remains separate

```bash
bash scripts/publish_daily_performance.sh --dry-run
bash scripts/publish_daily_performance.sh --apply
bash scripts/publish_daily_performance.sh --push
```

`Pre-match archive` links a receipt to Public V2 settlement only when date, competition, teams, market, line, direction and price match uniquely; otherwise it shows `UNLINKED` and does **not** silently add the receipt to profit. The site should never conflate retrospective quote processing with genuinely prospective GitHub publication.
