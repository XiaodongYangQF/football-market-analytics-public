#!/usr/bin/env bash
# Explicit, reviewed Local Public -> GitHub Public release.
# Never accesses the Private runtime, model, or internal ledgers.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
MODE="${1:---dry-run}"
case "$MODE" in
  --dry-run) exec python scripts/update_public_performance.py "${@:2}" ;;
  --apply|--push) ;;
  *) echo "Usage: $0 [--dry-run|--apply|--push] [--snapshot /path/to/tracker_snapshot.json]" >&2; exit 2 ;;
esac
python scripts/update_public_performance.py --apply "${@:2}"
python scripts/security_check.py
python -m pytest -q
if [ "$MODE" = --apply ]; then
  echo "Data updated locally; review it before pushing. No network publication performed."
  exit 0
fi

# Never create a public repository implicitly or stage unrelated files.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo 'STOP: No Git repo. Use the separately reviewed initial publish_github.sh first.' >&2
  exit 2
fi
if [ "$(git branch --show-current)" != main ]; then
  echo 'STOP: Expected main branch. Review your Git status.' >&2
  exit 2
fi
if ! command -v gh >/dev/null || ! gh auth status >/dev/null 2>&1; then
  echo 'STOP: gh not authenticated. Run gh auth login.' >&2
  exit 2
fi
REMOTE="$(git remote get-url origin 2>/dev/null || true)"
case "$REMOTE" in
  https://github.com/XiaodongYangQF/football-market-analytics-public|https://github.com/XiaodongYangQF/football-market-analytics-public.git|git@github.com:XiaodongYangQF/football-market-analytics-public.git) ;;
  *) echo "STOP: Unexpected origin remote: $REMOTE" >&2; exit 2 ;;
esac
if [ -n "$(git diff --cached --name-only)" ]; then
  echo 'STOP: Existing staged files found. Unstage/review them before the daily data-only push.' >&2
  exit 2
fi
if ! git diff --quiet -- app.py fma_portfolio scripts tests requirements.txt requirements-dev.txt; then
  echo 'STOP: Local code changes detected. Daily release must not silently include model/app changes.' >&2
  exit 2
fi

git add -- data/public_v2.json data/public_release_manifest.json
if git diff --cached --quiet; then
  echo 'No performance-data changes to push.'
  exit 0
fi
echo 'Public data files queued for GitHub:'
git diff --cached --stat
printf 'This action permanently discloses curated public records in Git history. Type PUBLISH: '
read -r answer
if [ "$answer" != PUBLISH ]; then
  git reset -q -- data/public_v2.json data/public_release_manifest.json
  echo 'Canceled before committing.'
  exit 1
fi

git commit -m "data: update public V2 simulated performance"
git push origin main
echo 'PUBLISHED: https://github.com/XiaodongYangQF/football-market-analytics-public'
