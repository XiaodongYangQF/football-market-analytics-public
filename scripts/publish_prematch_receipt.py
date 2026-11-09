#!/usr/bin/env python3
"""P8.1E: preview by default; --publish explicitly creates a GitHub Issue + JSON mirror.

No Private paths or model execution. Reads P7.4 browser-exported JSON only.
Remote GitHub server creation time is the publication evidence (not git dates).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fma_portfolio.p7.saved_forecasts import parse_archive, SavedForecastsError
from fma_portfolio.eligibility import classify_fixture
from fma_portfolio.prematch_receipts import (
    REPO, ReceiptError, body_for_issue, batch_from_issue_body, make_batch,
    make_receipt, published_fixture_keys, read_receipts, receipt_path, stamp, utc, validate_receipt,
)


def _run(cmd: list[str], *, timeout: int = 40) -> str:
    try:
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                              timeout=timeout, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise ReceiptError(f"Command unavailable/timed out: {cmd[0]}") from exc
    if proc.returncode:
        # Do not echo tokens or raw data. Github errors can contain sensitive args.
        raise ReceiptError(f"{cmd[0]} failed ({proc.returncode}); review credentials, repo and network")
    return proc.stdout.strip()


def _gh_json(endpoint: str, *, method: str = "GET", fields: dict[str, str] | None = None) -> dict:
    command = ["gh", "api", "-X", method, endpoint,
               "-H", "Accept: application/vnd.github+json"]
    for key, value in (fields or {}).items():
        command.extend(["-f", f"{key}={value}"])
    try:
        data = json.loads(_run(command))
    except json.JSONDecodeError as exc:
        raise ReceiptError("GitHub API returned non-JSON output") from exc
    if not isinstance(data, dict):
        raise ReceiptError("GitHub API returned unexpected data")
    return data


def _verify_git_ready(*, resume: bool = False, allowed_file: str = "", batch_id: str = "") -> None:
    if _run(["git", "rev-parse", "--is-inside-work-tree"]) != "true":
        raise ReceiptError("Initialize and publish the GitHub repository first")
    if _run(["git", "branch", "--show-current"]) != "main":
        raise ReceiptError("Public receipt publishing requires main branch")
    remote = _run(["git", "remote", "get-url", "origin"])
    if remote not in {f"https://github.com/{REPO}", f"https://github.com/{REPO}.git",
                      f"git@github.com:{REPO}.git"}:
        raise ReceiptError("Unexpected origin GitHub repository")
    tracked = _run(["git", "status", "--porcelain", "--untracked-files=no"])
    if tracked:
        changed = set(filter(None, (_run(["git", "diff", "--name-only"]) + "\n" +
                                   _run(["git", "diff", "--cached", "--name-only"])).splitlines()))
        if not resume or changed != {allowed_file}:
            raise ReceiptError("Commit/review unrelated tracked changes before publishing a receipt")
    _run(["git", "fetch", "origin", "main"])
    if _run(["git", "rev-list", "--count", "HEAD..origin/main"]) != "0":
        raise ReceiptError("Local branch is behind origin/main: pull before publishing")
    ahead = int(_run(["git", "rev-list", "--count", "origin/main..HEAD"]))
    if ahead:
        last_subject = _run(["git", "log", "-1", "--format=%s"])
        if not resume or ahead != 1 or last_subject != f"receipt: public pre-match batch {batch_id}":
            raise ReceiptError("Unpushed local commits present: review and push first")
    repo = _gh_json(f"repos/{REPO}")
    if repo.get("private") is not False or repo.get("has_issues") is not True:
        raise ReceiptError("GitHub repository must be PUBLIC with Issues enabled")
    _run([sys.executable, "scripts/security_check.py"])
    _run([sys.executable, "-m", "pytest", "-q"], timeout=120)


def _existing_issue(batch: dict, resume_issue: int | None = None) -> dict | None:
    if resume_issue is not None:
        issue = _gh_json(f"repos/{REPO}/issues/{resume_issue}")
        if batch_from_issue_body(issue.get("body")) != batch:
            raise ReceiptError("Supplied Issue is not the selected immutable batch")
        return issue
    query = f"repo:{REPO} is:issue in:title FMA-PREMATCH-{batch['batch_id']}"
    results = _gh_json("search/issues", fields={"q": query, "per_page": "20"})
    hits = results.get("items", [])
    if len(hits) > 1:
        raise ReceiptError("Multiple issues found with the same batch ID; manual review required")
    if hits:
        issue = _gh_json(f"repos/{REPO}/issues/{hits[0]['number']}")
        if batch_from_issue_body(issue.get("body")) != batch:
            raise ReceiptError("Existing GitHub Issue body differs: do not overwrite it")
        return issue
    return None


def _save_atomic(path: Path, receipt: dict) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        validate_receipt(old)
        original = {k: v for k, v in old.items() if k != "github_body_checked_at_utc"}
        new = {k: v for k, v in receipt.items() if k != "github_body_checked_at_utc"}
        if original != new:
            raise ReceiptError("Existing committed receipt differs; refusing to overwrite")
        return old
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".incoming-", suffix=".tmp", delete=False) as fh:
        tmp = Path(fh.name)
        try:
            fh.write(payload)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    os.replace(tmp, path)
    return receipt


def _select(records: list[dict], args) -> list[dict]:
    if not (args.record_id or args.fixture_date or args.competition or args.saved_after):
        raise ReceiptError("Explicit fixture/date/competition/saved-after selector required; no archive-wide publication")
    wanted = set(args.record_id or [])
    if wanted and len(wanted) != len(args.record_id):
        raise ReceiptError("Duplicate --record-id selector")
    selected = []
    for row in records:
        if wanted and row["record_id"] not in wanted:
            continue
        if args.fixture_date and row["fixture_date"] != args.fixture_date:
            continue
        if args.competition and row["competition"].casefold() != args.competition.casefold():
            continue
        if args.saved_after and utc(row["saved_at_utc"]) < utc(args.saved_after):
            continue
        selected.append(row)
    if wanted and wanted != {r["record_id"] for r in selected}:
        raise ReceiptError("Some requested IDs are missing or excluded by other filters")
    if not selected:
        raise ReceiptError("No saved forecasts match your explicit selection")
    return selected


def check_selected_coverage(records: list[dict]) -> None:
    """P8.1C-2E: never post NEW official receipts for excluded fixtures.

    Archived Issues remain unchanged; this only restricts future publication.
    """
    league_by_name = {'Premier League':'E0','Bundesliga':'D1','La Liga':'SP1',
                      'Serie A':'I1','Ligue 1':'F1'}
    for row in records:
        league = league_by_name.get(row['competition'])
        decision = classify_fixture(league,row['home_team'],row['away_team'],row['fixture_date'])
        if decision.status != 'ELIGIBLE':
            raise ReceiptError('New prematch receipt blocked: ' + decision.reason +
                               ' (INELIGIBLE/UNVERIFIED is not NO SIGNAL)')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path, help="P7.4 exported saved_forecasts.json")
    parser.add_argument("--kickoff-utc", required=True, help="UTC 2026-11-14T14:30:00Z (user-declared)")
    parser.add_argument("--fixture-date", help="Select original fixture date YYYY-MM-DD")
    parser.add_argument("--competition", help="Select exact display name, e.g. Bundesliga")
    parser.add_argument("--saved-after", help="Only select records saved at/after this ISO UTC instant")
    parser.add_argument("--record-id", action="append", help="Select exact forecast UUID; repeatable")
    parser.add_argument("--kickoff-basis", default="USER_DECLARED_UNVERIFIED",
                        help="Public kickoff-source description (not independently validated)")
    parser.add_argument("--quote-source", default="User-entered market quotes; independent execution unverified")
    parser.add_argument("--publish", action="store_true", help="CREATE GitHub Issue and push JSON mirror")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation (must also provide --publish)")
    parser.add_argument("--resume-issue", type=int, help="Reuse existing Issue after a failed push; no new Issue")
    args = parser.parse_args()
    if args.yes and not args.publish or args.resume_issue and not args.publish:
        parser.error("--yes/--resume-issue requires --publish")
    try:
        try:
            records = parse_archive(args.archive.read_bytes())
        except (SavedForecastsError, OSError) as exc:
            raise ReceiptError(f"Cannot read P7.4 public saved archive: {exc}") from exc
        selection = _select(records, args)
        check_selected_coverage(selection)
        batch = make_batch(selection, args.kickoff_utc, kickoff_basis=args.kickoff_basis,
                           quote_source=args.quote_source)
        cutoff = utc(batch["kickoff_utc"])
        print(f"Batch: {batch['batch_id']} | declared kickoff {batch['kickoff_utc']}")
        print("GitHub publication is authoritative for its server time; kickoff and quotes are user-declared.")
        print("These fields will become permanently public:")
        for r in batch["records"]:
            print(f"  {r['fixture_date']} | {r['competition']} | {r['home_team']} vs {r['away_team']}"
                  f" | saved {r['saved_at_utc']}")
            print(f"    AH home-line {r['ah_line']:+g} | home/away odds {r['ah_home_odds']:.3f}/{r['ah_away_odds']:.3f}"
                  f" | forecast: {r['ah_direction'] if r['ah_status']=='FORECAST' else 'NO SIGNAL'}")
            print(f"    OU line {r['asian_line']:g} | over/under odds {r['asian_over_odds']:.3f}/{r['asian_under_odds']:.3f}"
                  f" | forecast: {r['ou_direction'] if r['ou_status']=='FORECAST' else 'NO SIGNAL'}")
            print(f"    Fixed 2.5 calibration over/under: {r['fixed_over_odds']:.3f}/{r['fixed_under_odds']:.3f}"
                  f" | policy {r['policy_version']}")
        if not args.publish:
            print("DRY RUN: no GitHub Issue, commit or push was made. Use --publish to publish.")
            return 0
        now = datetime.now(timezone.utc)
        if now >= cutoff and not args.resume_issue:
            raise ReceiptError("Kickoff already passed locally. Never create a new Issue retroactively; use --resume-issue only to mirror an Issue that already exists")
        if max(utc(r["saved_at_utc"]) for r in batch["records"]) > now + timedelta(seconds=10):
            raise ReceiptError("Forecast's local saved clock is ahead of current UTC time")
        archive = read_receipts(ROOT)
        # The same batch may be present locally after a failed git push.
        # Recovery must never create a second Issue or hide a conflicting batch.
        other_batches = [entry for entry in archive if entry["batch"]["batch_id"] != batch["batch_id"]]
        repeated = published_fixture_keys(other_batches).intersection({
            (r["fixture_date"], r["competition"].casefold(), r["home_team"].casefold(), r["away_team"].casefold())
            for r in batch["records"]})
        if repeated:
            raise ReceiptError("A fixture already exists in the published archive; block cherry-picked re-posts")
        destination = receipt_path(ROOT, batch)
        relative = destination.relative_to(ROOT).as_posix()
        _verify_git_ready(resume=bool(args.resume_issue), allowed_file=relative,
                          batch_id=batch["batch_id"])
        if not args.yes:
            answer = input("Create a PUBLIC GitHub Issue with the full forecast data? Type PUBLISH: ").strip()
            if answer != "PUBLISH":
                print("CANCELED: nothing was published")
                return 1
        issue = _existing_issue(batch, args.resume_issue)
        if issue is None:
            if datetime.now(timezone.utc) >= cutoff:
                raise ReceiptError("Kickoff passed during checks; nothing new published")
            title = f"FMA-PREMATCH-{batch['batch_id']} | {batch['kickoff_utc']} | {len(batch['records'])} fixtures"
            issue = _gh_json(f"repos/{REPO}/issues", method="POST",
                             fields={"title": title, "body": body_for_issue(batch)})
        receipt = make_receipt(batch, issue)
        path = receipt_path(ROOT, batch)
        receipt = _save_atomic(path, receipt)
        rel = path.relative_to(ROOT).as_posix()
        try:
            _run([sys.executable, "scripts/security_check.py"])
            _run(["git", "add", "--", rel])
            if _run(["git", "diff", "--cached", "--name-only"]):
                _run(["git", "commit", "-m", f"receipt: public pre-match batch {batch['batch_id']}"])
            if int(_run(["git", "rev-list", "--count", "origin/main..HEAD"])) > 0:
                _run(["git", "push", "origin", "main"], timeout=75)
        except ReceiptError:
            print(f"WARNING: Issue exists at {receipt['github_issue_url']} but Git JSON mirror is not yet confirmed pushed.")
            print("Do NOT create another issue. Review git status and push the existing commit, or use --resume-issue.")
            raise
        print(f"PUBLIC ISSUE: {receipt['github_issue_url']}")
        print(f"GITHUB CREATED (UTC): {receipt['github_created_at_utc']}")
        print(f"DECLARED KICKOFF: {batch['kickoff_utc']}")
        print(f"RESULT: {receipt['publication_class']} (relative to USER-DECLARED kickoff)")
        print(f"MIRRORED: {rel}")
        return 0
    except (ReceiptError, ValueError, KeyboardInterrupt) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
