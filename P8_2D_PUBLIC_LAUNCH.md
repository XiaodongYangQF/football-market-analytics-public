# P8.2D — Public Website and README Presentation Update (2026-11-09)

This is a **public Portfolio presentation-only patch**. It does not alter Private, Local Public 8502, frozen science, AH/OU trading rules, existing P&L, public JSON data or private parity evidence.

## Delivered changes

1. Default page becomes `Performance overview`. Navigation order: Performance overview → Pre-match archive → Forecast ledger → Methodology & limits → Interactive forecast.
2. A sidebar link exposes the public repository source and record history.
3. README presents the real Streamlit site, GitHub repository and public Issues, and clearly states that hosted real-model prediction execution is **not** enabled.
4. Three static regression tests guard the homepage and public disclosure content.

## Original patch installation

```bash
cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_2D_Public_Presentation_Patch_20261109.zip" -d "$HOME/Projects"
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/security_check.py
python -m pytest -q
```

When paired with the preceding complete patch set, the original acceptance target was 139 passing tests. Verify `git status --short` for unrelated or private changes before publication.

## Repository metadata and actual deployment

The initial P8.2D commit was `7d9455f` on public `main`. Repository metadata can be inspected or updated using:

```bash
gh repo edit XiaodongYangQF/football-market-analytics-public \
  --homepage "https://football-market-analytics.streamlit.app/" \
  --description "Public football AH/OU research: simulated performance and auditable pre-match forecast receipts"
gh repo view XiaodongYangQF/football-market-analytics-public \
  --json url,isPrivate,homepageUrl,description
```

## Public acceptance checklist

- The public site first displays `Performance overview`, not an unusable hosted model execution page.
- Settled counts, simulated P&L and ROI match the frozen Public V2 dataset.
- `Pre-match archive` is empty until a genuine prospective receipt is created; historic replays cannot be relabeled as publicly posted forecasts.
- Anonymous users cannot execute the Private model.
- README site link and GitHub About homepage point to the deployed public Streamlit app.

For the first real pre-match record use [P8_2E_FIRST_RECEIPT_ACCEPTANCE.md](P8_2E_FIRST_RECEIPT_ACCEPTANCE.md).
