# English-only public repository update — P8.2G

## Policy

All published repository documentation, README links, UI copy, source comments and operational instructions must remain in **English**. This affects only the independent public Portfolio. It does **not** translate or alter Private research files, Local Public (8502), prediction science, AH/OU rules, odds, forecasts or settlement data.

This patch supplies English equivalents for 14 historical operational handoff documents, updates README and the prematch receipt specification links, and adds an automated English-only check to CI.

## Install on Mac

Download the patch ZIP to `~/Downloads`, then:

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_2G_English_Only_Public_Docs_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/finish_english_only_migration.py
python scripts/finish_english_only_migration.py --apply
python scripts/check_public_english.py
python scripts/security_check.py
python -m pytest -q
```

The removal script backs up 14 legacy documents to `~/fma_patch_backups/p8_2g_english_migration`, **outside** the public repository, before deleting them. It refuses to remove tracked documents with uncommitted edits or overwrite an existing backup. Re-running it is safe if no legacy documents remain.

## Review and publish only documentation changes

```bash
git status --short
# Stage only the exact new/changed files in this language-only patch.
git add -- README.md docs/prematch_receipts.md .github/workflows/ci.yml \
  scripts/check_public_english.py scripts/finish_english_only_migration.py \
  tests/test_public_english.py ENGLISH_ONLY_UPDATE.md

git add -- \
  INSTALL.md \
  P8_1B_HANDOFF.md P8_1B_SCHEDULE_FIX.md \
  P8_1C_HOSTED_PILOT.md \
  P8_1C2_SCIENTIFIC_PARITY.md P8_1C2_RESUMABLE_MAC_BASELINE.md \
  P8_1C2_EXTRACTION_DIAGNOSTIC_FIX.md P8_1C2_MAC_TEST_HOTFIX.md \
  P8_1C2E_ELIGIBILITY_GATE.md \
  P8_1D_DAILY_PUBLISH_HANDOFF.md P8_1E_PREMATCH_RECEIPTS.md \
  P8_2D_PUBLIC_LAUNCH.md P8_2E_FIRST_RECEIPT_ACCEPTANCE.md \
  P8_2F_LOCAL_PUBLIC_RECEIPT_BRIDGE.md

# Stage deletions of only the tracked language-specific legacy docs.
git add -u -- ':(glob)*_CN.md'

git diff --cached --name-status
git diff --cached --check
git commit -m "docs: convert public portfolio documentation to English"
git push origin main
```

**Important:** Inspect the staged list before committing. It should contain only 14 added English manuals, deletion of their already tracked legacy counterparts, README, the internal prematch documentation reference, one CI workflow, the two language-check/migration scripts, their test file, and this guide. The previous `P8.2F` language-specific guide might have been untracked; if so Git has no deletion to stage for it. Do not use a broad `git add .` or stage local prediction data.

The public Streamlit app will continue to run as before. No new Issue or forecast is created by this change.
