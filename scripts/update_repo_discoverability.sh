#!/usr/bin/env bash
set -euo pipefail

REPO="XiaodongYangQF/football-market-analytics-public"
TOPICS="football-analytics,sports-analytics,sports-betting,betting-odds,asian-handicap,python,streamlit,data-science,statistics,probability,quantitative-research,quantitative-finance,market-implied-information,backtesting,data-visualization"
DESCRIPTION="Football AH/OU research: market-implied information, Asian-line settlement, simulated performance and auditable public records"

if [[ "${1:-}" != "--apply" ]]; then
  printf 'DRY RUN — no GitHub repository metadata changed.\n\n'
  printf 'Repository: %s\nTopics: %s\nDescription: %s\n' "$REPO" "$TOPICS" "$DESCRIPTION"
  printf '\nAfter reviewing, run: bash scripts/update_repo_discoverability.sh --apply\n'
  exit 0
fi

command -v gh >/dev/null || { echo 'ERROR: GitHub CLI (gh) is required.' >&2; exit 2; }
gh auth status >/dev/null

REMOTE="$(git remote get-url origin)"
case "$REMOTE" in
  "https://github.com/$REPO"|"https://github.com/$REPO.git"|"git@github.com:$REPO"|"git@github.com:$REPO.git") ;;
  *) echo "ERROR: Unexpected origin: $REMOTE" >&2; exit 2;;
esac

printf 'Updating GitHub About metadata for %s...\n' "$REPO"
gh repo edit "$REPO" --add-topic "$TOPICS" --description "$DESCRIPTION" --homepage "https://football-market-analytics.streamlit.app/"
printf '\nVerified repository metadata:\n'
gh repo view "$REPO" --json description,homepageUrl,repositoryTopics --jq '{description,homepageUrl,topics:[.repositoryTopics[].name]}'
