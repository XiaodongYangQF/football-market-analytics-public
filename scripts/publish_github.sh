#!/usr/bin/env bash
# Explicit opt-in publisher. Does not read or modify the original Private project.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
REPO="${FMA_GH_REPO:-XiaodongYangQF/football-market-analytics-public}"
if ! command -v gh >/dev/null 2>&1; then
  echo 'GitHub CLI (gh) is not installed. Run: brew install gh' >&2
  exit 2
fi
gh auth status >/dev/null || { echo 'Run gh auth login first' >&2; exit 2; }
python3 scripts/security_check.py
python3 -m pytest -q
if gh repo view "$REPO" >/dev/null 2>&1; then
  echo "STOP: $REPO already exists. Refusing to overwrite or force-push." >&2
  exit 2
fi
if [ ! -d .git ]; then
  git init -b main
fi
if [ -n "$(git remote)" ]; then
  echo 'STOP: Existing git remote found; review it manually before publishing.' >&2
  exit 2
fi
git add .
echo 'Files staged for a NEW PUBLIC repository:'
git diff --cached --stat
if [ -z "$(git diff --cached --name-only)" ]; then
  echo 'STOP: No files staged.' >&2
  exit 2
fi
printf '\nThis will CREATE a PUBLIC repository: %s\nType PUBLISH to continue: ' "$REPO"
read -r answer
if [ "$answer" != PUBLISH ]; then
  echo 'Canceled.'
  exit 1
fi
git commit -m "Initial public research portfolio release"
gh repo create "$REPO" --public --source=. --remote=origin --push
echo "Published: https://github.com/$REPO"
