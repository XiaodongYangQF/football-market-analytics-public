# P8.2F — Local Public to GitHub Pre-match Receipt Bridge

## Intended production workflow

**Single input in Private → existing Private-to-Local Public publication applies frozen Public V2 strategy → local-only read-only source exporter verifies full market quotes → public-safe receipt feed → GitHub Portfolio publisher creates a prospective Issue → P8.1D publishes results after settlement.**

This patch does **not** modify the frozen Private model, existing Public V2 conversion rules, the Local Public 8502 UI, or hosted cloud access to private storage. It adds two separate CLI utilities:

- `football_market_analytics_v2_2/scripts/export_public_receipt_feed.py`: installed in the existing Private/Local Public project; reads local `runtime_data/cases`, `runtime_data/ledgers`, and `public_data/tracker_snapshot.json` **read-only**. It exports the **already confirmed** Public V2 direction, not a re-derived direction from Private. It does not communicate with GitHub.
- `football-market-analytics-public/scripts/publish_local_public_receipt.py`: installed in the public Portfolio; consumes only an allowlisted local `public_data/receipt_exports/*.json` feed and delegates to the existing P8.1E receipt publisher. It defaults to dry run. Actual publication requires explicit `--publish` and `PUBLISH` confirmation.

**Why two tools?** The Local Public tracker stores only selected-side prices, not the complete AH, OU and fixed-2.5 two-sided quotes or original analysis save time. Those fields cannot be reconstructed or backdated. The local exporter reads the existing private evidence, checks it against confirmed Local Public records and exports only approved fields. GitHub itself never reads Private.

## 1. Install and validate the original bridge patch

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_2F_Local_Public_Receipt_Bridge_Patch_20261109.zip" -d "$HOME/Projects"

cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q

cd "$HOME/Projects/football_market_analytics_v2_2"
python -m pytest -q tests/test_public_receipt_feed_export.py
```

P8.2F originally added four tests in the public Portfolio and eight tests in the local exporter project. It did not rewrite existing scientific code or datasets.

## 2. Produce an authentic confirmed Local Public record first

Enter AH, main OU and fixed-2.5 both-sided odds **once** in Private, run the original science and confirm the result. Complete the existing publication to Local Public port 8502. The tracker must contain the fixture's `POST_ACTIVATION_V2` entries.

A forecast entered **only in owner-local 8504** is a separate session record: it is **not** evidence of a confirmed 8502 release and must not be manufactured into one. This distinction matters for the initial Liverpool vs Man United test, which was saved only in 8504. No conversion script can properly invent a missing Private-to-Local Public publication.

## 3. Export a sanitized receipt feed on the owner's Mac

The following match is a **command-format example**. Team text must match Local Public exactly and the fixture must have genuinely passed the normal publication process. Use the real Private root if it differs.

Dry run:

```bash
cd "$HOME/Projects/football_market_analytics_v2_2"
conda activate fma-portfolio
python scripts/export_public_receipt_feed.py \
  --private-root "$HOME/Projects/football_market_analytics_v2_2/runtime_data" \
  --fixture-date 2026-11-22 \
  --competition "Premier League" \
  --fixture "Liverpool vs Man United"
```

After reviewing the output, append `--apply` **on the same complete command**, ensuring the previous shell line ends with `\`. This only writes a sanitized **local** feed file; it does not create a GitHub Issue:

```text
$HOME/Projects/football_market_analytics_v2_2/public_data/receipt_exports/2026-11-22_<hash>.json
```

The exporter prints the exact created path. It does not overwrite an existing artifact with different content. Multiple `--fixture` selectors can be supplied (maximum 20), but only fixtures with the **same verified actual kickoff** should be batched for subsequent public publication.

### Fail-closed conditions

The exporter refuses to proceed if the fixture lacks unique complete AH+OU `POST_ACTIVATION_V2` entries, a market is `NOT_RECORDED` instead of a confirmed forecast or explicit `NO SIGNAL`, Private and Public records reflect different analyses, full AH/OU/fixed-2.5 quote evidence is missing, the final selected-side quote disagrees with the saved Private source, or fixture identity is ambiguous. It never reruns science or changes winning/losing decisions to pass the checks.

## 4. Preview the approved feed in the Portfolio

Use the **actual** filename reported in step 3, and verify the UTC kickoff separately:

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/publish_local_public_receipt.py \
  --feed "$HOME/Projects/football_market_analytics_v2_2/public_data/receipt_exports/2026-11-22_<actual_hash>.json" \
  --fixture-date 2026-11-22 \
  --competition "Premier League" \
  --kickoff-utc "2026-11-22T16:30:00Z" \
  --kickoff-basis "Official fixture schedule, manually verified" \
  --quote-source "User-entered Local Public odds; capture source and time unverified"
```

Without `--publish`, the existing P8.1E program prints proposed final directions, complete odds, saved timestamps and batch identity without performing any public write. The example kickoff is operator-supplied; always verify the live official schedule before a real release.

## 5. Publish before kickoff, only with approval

Only after a successful dry run and exact manual inspection, append `--publish` to the **same** command and type `PUBLISH` when prompted. P8.1E checks the eligible cohort, git state and duplicates, creates a GitHub Issue, compares platform `created_at` to the operator-declared kickoff, and pushes the JSON mirror. The result `ON_TIME_DECLARED` is not third-party certification of actual kickoff or quote executability.

If the Issue exists but the push fails, **never create a duplicate Issue**. Recover the original one using documented P8.1E resume behavior.

## 6. Post-match performance

```bash
cd "$HOME/Projects/football-market-analytics-public"
bash scripts/publish_daily_performance.sh --dry-run
bash scripts/publish_daily_performance.sh --apply
bash scripts/publish_daily_performance.sh --push
```

Receipts and performance remain independent evidence tracks. This bridge does not change existing ROI/P&L or double-count a new forecast. The public archive links a receipt to a settled record only when the original identifiers, market, direction, handicap/total line and quote price agree uniquely.

## Acceptance boundary

The bridge completed isolated unit and CLI dry-run validation. It has **not yet** been verified end-to-end against a genuinely confirmed new Private → Local Public fixture on the owner's Mac, nor does it imply a real GitHub Issue was published. Port 8502 still has no one-click GitHub Publish button; a future UI wrapper may offer one, but explicit preview and approval should remain mandatory.
