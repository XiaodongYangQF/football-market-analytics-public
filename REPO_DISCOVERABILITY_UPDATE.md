# Repository discoverability and README update

This update is designed for a broad audience: football-market researchers, data scientists, quantitative finance professionals, statisticians, and Python/Streamlit users.

## Changes

- Replaces the technical-heavy root README with a reader-first overview, an actual user-supplied dashboard screenshot, scientific motivation and accurate project-status distinctions.
- Moves the previous complete technical README to `docs/maintainer_reference.md`, preserving detailed operator and implementation information.
- Adds a small README regression test.
- Adds a GitHub CLI helper to add accurate cross-disciplinary topics and improve the repository description and homepage metadata.
- Does **not** alter models, algorithms, public data, dashboard UI, GitHub receipts, or performance calculations.

**Research-integrity boundary:** The private P1/P2 OU research already implements **parametric Poisson-equivalent total-goals distribution inference** from fixed O/U 2.5 prices, and settlement-consistent translation to main Asian Total quotations. The public repository does **not** contain that private inference engine. Nonparametric/full joint distribution identification and out-of-sample probability-calibration testing remain research directions. Market-to-Poisson parameter fitting is **not** the same as empirical probability calibration. Bookmaker odds are not equated with arbitrage-free option-implied risk-neutral densities.

## Installation on macOS

Download the ZIP into Downloads, then:

```bash
cd "$HOME/Projects/football-market-analytics-public"
git status --short

cd "$HOME/Projects"
unzip -o "$HOME/Downloads/FMA_Repository_Discoverability_README_Update_20261110.zip" -d "$HOME/Projects"

cd "$HOME/Projects/football-market-analytics-public"
conda activate fma-portfolio
python scripts/check_public_english.py
python scripts/security_check.py
python -m pytest -q
```

Preview in your GitHub reader at the local file `README.md`. Only six files are introduced or changed.

## Publish the README

```bash
git add -- README.md docs/maintainer_reference.md assets/dashboard-overview.png tests/test_public_readme.py scripts/update_repo_discoverability.sh REPO_DISCOVERABILITY_UPDATE.md
GIT_PAGER=cat git diff --cached --name-status
git diff --cached --check
git commit -m "docs: position football research for broader quantitative audience"
git push origin main
```

## Preview and update GitHub topics

The script has a no-write default:

```bash
bash scripts/update_repo_discoverability.sh
```

After reviewing the exact list:

```bash
bash scripts/update_repo_discoverability.sh --apply
```

The command **adds** topics and updates only the description and homepage. It does not delete existing topics, modify branch visibility or change permissions. GitHub allows up to 20 topics. If the existing repository already has many topics, reconcile manually before applying.

## Verify

```bash
git status --short
gh repo view XiaodongYangQF/football-market-analytics-public --json description,homepageUrl,repositoryTopics --jq '{description,homepageUrl,topics:[.repositoryTopics[].name]}'
```

Read the live README at https://github.com/XiaodongYangQF/football-market-analytics-public .
