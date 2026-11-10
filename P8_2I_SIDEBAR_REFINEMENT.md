# P8.2I — Research Sidebar Refinement

## Scope

This is a visual-only refinement of the public Streamlit sidebar, influenced by
clear section hierarchy and active-navigation styling. The application still
uses its existing native Streamlit radio navigation and multiselect controls.

New layout:

- **FMA Research** — compact brand mark and research subtitle
- **RESEARCH** — the same five pages in the same order; active pill styling
- **FILTERS** — native Market and Competition controls, with softer styling
- **PUBLIC DATA** — fixed-policy and simulated-results disclosure
- **LINKS** — source repository and public Issues

The design uses the app's existing navy/teal palette. No external assets,
JavaScript, live quote endpoints, or scientific model dependencies were added.

## Installation (Mac Terminal)

1. From your existing `~/Projects/football-market-analytics-public` repo, make
   sure `git status --short` is empty. If not, review and save those changes.
2. Keep a local backup of `app.py` before unzipping the patch.
3. Unzip the patch **into `~/Projects`**, not directly into the repo.
4. Run the checks and preview locally.

```bash
cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio

git status --short
mkdir -p "$HOME/fma_patch_backups"
cp app.py "$HOME/fma_patch_backups/app_p8_2i_before.py"

cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_P8_2I_Sidebar_Refinement_20261110.zip" -d "$HOME/Projects"

cd "$HOME/Projects/football-market-analytics-public"
python scripts/check_public_english.py
python scripts/security_check.py
python -m pytest -q
streamlit run app.py --server.port 8505
```

Open <http://localhost:8505> to check the five sidebar pages and the Market and
Competition filters before publishing. The local preview can be stopped with
Ctrl+C. If the port is in use, choose another free port.

## Safe commit

```bash
cd "$HOME/Projects/football-market-analytics-public"
git diff --check
GIT_PAGER=cat git diff --stat

git add -- app.py tests/test_sidebar_polish.py P8_2I_SIDEBAR_REFINEMENT.md
git diff --cached --check
GIT_PAGER=cat git diff --cached --name-status

git commit -m "ui: refine public research sidebar navigation"
git push origin main
```

Only stage those three paths, after successful tests and review. The backup under `~/fma_patch_backups/` stays outside the repository.

## Rollback

If the patch is installed but not committed:

```bash
git restore -- app.py
# Review the two new files before deciding whether to delete them.
```

If it has been committed and pushed, revert that specific commit through Git
rather than rewriting public history.

## Notes

The sidebar controls are real Streamlit widgets. Visual styling for the active
radio label uses CSS `:has(input:checked)` in current browsers; unsupported
browsers retain the native checked radio indicator and functional navigation.
The Interactive forecast page remains subject to its existing hosted-model
restrictions.
