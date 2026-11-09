"""P8.1E: public, provider-timestamped forecasts; never re-run a model.

A *GitHub Issue*, not an editable local clock or git author date, is the initial
public evidence. A checked, committed JSON mirror is for browsing. GitHub
issues are editable/deletable: this is auditable evidence, not notarization.
"""
from __future__ import annotations

from datetime import datetime, date, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from fma_portfolio.p7.saved_forecasts import validate_saved_record, SavedForecastsError

BATCH_SCHEMA = "FMA_PREMATCH_BATCH_V1"
RECEIPT_SCHEMA = "FMA_GITHUB_PREMATCH_RECEIPT_V1"
BEGIN = "<!-- FMA_PREMATCH_JSON_BEGIN -->"
END = "<!-- FMA_PREMATCH_JSON_END -->"
REPO = "XiaodongYangQF/football-market-analytics-public"
REPO_ISSUES = f"https://github.com/{REPO}/issues/"
MAX_BATCH = 16
MAX_FILES = 2500
_ALLOWED_BATCH = {"schema", "batch_id", "kickoff_utc", "kickoff_basis", "quote_source", "records"}
_ALLOWED_RECEIPT = {"schema", "batch", "batch_sha256", "github_issue_number",
                    "github_issue_url", "github_created_at_utc", "github_body_checked_at_utc",
                    "publication_class"}


class ReceiptError(ValueError):
    pass


def utc(value: str) -> datetime:
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("Timezone required")
        return instant.astimezone(timezone.utc)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ReceiptError("Timestamp must be ISO-8601 with a UTC offset") from exc


def stamp(value: str) -> str:
    instant = utc(value)
    return instant.isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def sha256(obj: dict) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def _clean_note(value: str, label: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 180:
        raise ReceiptError(f"{label} must contain 1–180 characters")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ReceiptError(f"Control character in {label}")
    if BEGIN in value or END in value:
        raise ReceiptError("Reserved receipt marker in text")
    return value.strip()


def _normalize_rows(rows: list[dict], kickoff: str) -> list[dict]:
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_BATCH:
        raise ReceiptError(f"One public batch must contain 1–{MAX_BATCH} fixtures")
    ko = utc(kickoff)
    result = []
    seen_records, seen_fixtures = set(), set()
    for item in rows:
        try:
            row = validate_saved_record(item)
        except SavedForecastsError as exc:
            raise ReceiptError(f"Invalid P7.4 forecast record: {exc}") from exc
        if BEGIN in canonical(row) or END in canonical(row):
            raise ReceiptError("Reserved marker in public forecast")
        saved = utc(row["saved_at_utc"])
        if saved >= ko:
            raise ReceiptError(f"Forecast generated on/after stated kickoff: {row['record_id']}")
        if abs((date.fromisoformat(row["fixture_date"]) - ko.date()).days) > 1:
            raise ReceiptError("Fixture date and claimed kickoff day differ by more than one day")
        fixture = (row["fixture_date"], row["competition"].casefold(),
                   row["home_team"].casefold(), row["away_team"].casefold())
        if row["record_id"] in seen_records or fixture in seen_fixtures:
            raise ReceiptError("Duplicate forecast ID or fixture within batch")
        seen_records.add(row["record_id"])
        seen_fixtures.add(fixture)
        result.append(row)
    return sorted(result, key=lambda r: (r["competition"], r["home_team"], r["away_team"], r["record_id"]))


def make_batch(rows: list[dict], kickoff_utc: str, *,
               kickoff_basis: str = "USER_DECLARED_UNVERIFIED",
               quote_source: str = "User-entered market quotes; independent execution unverified") -> dict:
    kickoff = stamp(kickoff_utc)
    core = {"schema": BATCH_SCHEMA, "kickoff_utc": kickoff,
            "kickoff_basis": _clean_note(kickoff_basis, "kickoff_basis"),
            "quote_source": _clean_note(quote_source, "quote_source"),
            "records": _normalize_rows(rows, kickoff)}
    batch = {**core, "batch_id": sha256(core)[:20]}
    validate_batch(batch)
    return batch


def validate_batch(batch: Any) -> None:
    if not isinstance(batch, dict) or set(batch) != _ALLOWED_BATCH or batch["schema"] != BATCH_SCHEMA:
        raise ReceiptError("Unexpected prematch batch schema or fields")
    normalized = _normalize_rows(batch["records"], stamp(batch["kickoff_utc"]))
    if normalized != batch["records"]:
        raise ReceiptError("Forecast rows must use canonical ordering and normalization")
    _clean_note(batch["kickoff_basis"], "kickoff_basis")
    _clean_note(batch["quote_source"], "quote_source")
    core = {k: batch[k] for k in _ALLOWED_BATCH if k != "batch_id"}
    if batch["batch_id"] != sha256(core)[:20]:
        raise ReceiptError("Batch ID/hash does not match its frozen content")
    if batch["kickoff_utc"] != stamp(batch["kickoff_utc"]):
        raise ReceiptError("Kickoff must use canonical UTC form")


def body_for_issue(batch: dict) -> str:
    validate_batch(batch)
    digest = sha256(batch)
    lines = [
        "# Football Market Analytics — public pre-match receipt",
        f"**Batch ID:** `{batch['batch_id']}`  ",
        f"**Canonical SHA-256:** `{digest}`  ",
        f"**Kickoff (declared UTC):** `{batch['kickoff_utc']}`  ",
        f"**Fixtures:** {len(batch['records'])}  ",
        "**Status:** Forecast inputs/output were submitted to GitHub. Kickoff and quote provenance are user-declared, not independently verified.",
        "",
        "Original forecasts must not be edited after posting. Add later results as separate records.",
        "A GitHub Issue is publicly inspectable, but its owner can edit or delete it; it is not immutable certification.",
        "",
        BEGIN,
        "```json",
        json.dumps(batch, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False),
        "```",
        END,
        "",
    ]
    return "\n".join(lines)


def batch_from_issue_body(body: str) -> dict:
    if not isinstance(body, str) or body.count(BEGIN) != 1 or body.count(END) != 1:
        raise ReceiptError("Missing/ambiguous canonical block in GitHub Issue")
    section = body.split(BEGIN, 1)[1].split(END, 1)[0].strip()
    if not (section.startswith("```json\n") and section.endswith("\n```")):
        raise ReceiptError("Invalid issue JSON block framing")
    try:
        batch = json.loads(section[len("```json\n"):-len("\n```")])
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ReceiptError("GitHub Issue JSON cannot be parsed") from exc
    validate_batch(batch)
    if f"`{sha256(batch)}`" not in body or f"`{batch['batch_id']}`" not in body:
        raise ReceiptError("Visible GitHub Issue hash/ID does not match body")
    return batch


def make_receipt(batch: dict, issue: dict, *, checked_at: str | None = None) -> dict:
    validate_batch(batch)
    if not isinstance(issue, dict) or not isinstance(issue.get("number"), int):
        raise ReceiptError("GitHub did not return a valid Issue")
    number = issue["number"]
    if number <= 0 or issue.get("html_url") != f"{REPO_ISSUES}{number}":
        raise ReceiptError("Unexpected GitHub Issue URL/repository")
    if issue.get("body") != body_for_issue(batch):
        raise ReceiptError("Remote Issue content differs from canonical forecast")
    created = stamp(issue.get("created_at"))
    status = "ON_TIME_DECLARED" if utc(created) < utc(batch["kickoff_utc"]) else "LATE_PUBLICATION"
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "batch": batch,
        "batch_sha256": sha256(batch),
        "github_issue_number": number,
        "github_issue_url": issue["html_url"],
        "github_created_at_utc": created,
        "github_body_checked_at_utc": stamp(checked_at or datetime.now(timezone.utc).isoformat()),
        "publication_class": status,
    }
    validate_receipt(receipt)
    return receipt


def validate_receipt(obj: Any) -> None:
    if not isinstance(obj, dict) or set(obj) != _ALLOWED_RECEIPT or obj["schema"] != RECEIPT_SCHEMA:
        raise ReceiptError("Invalid public receipt schema")
    validate_batch(obj["batch"])
    if obj["batch_sha256"] != sha256(obj["batch"]):
        raise ReceiptError("Public receipt content hash mismatch")
    number = obj["github_issue_number"]
    if type(number) is not int or number <= 0 or obj["github_issue_url"] != f"{REPO_ISSUES}{number}":
        raise ReceiptError("Public receipt Issue URL mismatch")
    created = stamp(obj["github_created_at_utc"])
    stamp(obj["github_body_checked_at_utc"])
    if created != obj["github_created_at_utc"]:
        raise ReceiptError("Non-canonical server timestamp")
    label = "ON_TIME_DECLARED" if utc(created) < utc(obj["batch"]["kickoff_utc"]) else "LATE_PUBLICATION"
    if obj["publication_class"] != label:
        raise ReceiptError("Incorrect pre-kickoff classification")
    if utc(obj["github_body_checked_at_utc"]) < utc(created):
        raise ReceiptError("Issue body checked before GitHub created it")
    if any(utc(r["saved_at_utc"]) > utc(created) for r in obj["batch"]["records"]):
        raise ReceiptError("Local forecast timestamp is later than GitHub publication")


def receipt_path(root: Path, batch: dict) -> Path:
    validate_batch(batch)
    return root / "data" / "forecast_receipts" / f"{batch['kickoff_utc'][:10]}_{batch['batch_id']}.json"


def read_receipts(root: Path) -> list[dict]:
    folder = root / "data" / "forecast_receipts"
    if not folder.is_dir():
        return []
    files = sorted(folder.glob("*.json"))
    if len(files) > MAX_FILES:
        raise ReceiptError("Receipt archive exceeds maximum size")
    result = []
    ids, games = set(), set()
    for file in files:
        if file.stat().st_size > 120_000:
            raise ReceiptError(f"Oversized receipt: {file.name}")
        try:
            obj = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            raise ReceiptError(f"Could not read {file.name}") from exc
        validate_receipt(obj)
        if file != receipt_path(root, obj["batch"]):
            raise ReceiptError(f"Unexpected receipt filename: {file.name}")
        if obj["batch"]["batch_id"] in ids:
            raise ReceiptError("Duplicate public batch")
        ids.add(obj["batch"]["batch_id"])
        for row in obj["batch"]["records"]:
            key = (row["fixture_date"], row["competition"].casefold(),
                   row["home_team"].casefold(), row["away_team"].casefold())
            if key in games:
                raise ReceiptError("Same fixture published in two public batches")
            games.add(key)
        result.append(obj)
    return sorted(result, key=lambda x: x["github_created_at_utc"], reverse=True)


def published_fixture_keys(receipts: list[dict]) -> set[tuple]:
    return {(r["fixture_date"], r["competition"].casefold(),
             r["home_team"].casefold(), r["away_team"].casefold())
            for item in receipts for r in item["batch"]["records"]}


def reconcile_public_settlement(forecast: dict, market: str, ledger: list[dict]) -> str:
    """Read-only, exact-quote link. Never infer a settlement from team/date alone.

    Receipt rows are NEVER added to the Public V2 P&L denominator. If either
    the settled market quote or direction differs, leave it unlinked.
    """
    if market not in ("AH", "OU"):
        raise ReceiptError("Unknown market in reconciliation")
    prefix = market.lower()
    no_signal = forecast[f"{prefix}_status"] == "NO_SIGNAL"
    direction = forecast[f"{prefix}_direction"] if not no_signal else "NO SIGNAL"
    line = forecast["ah_line"] if market == "AH" else forecast["asian_line"]
    if market == "AH":
        price = forecast["ah_home_odds"] if direction == "HOME" else forecast["ah_away_odds"]
    else:
        price = forecast["asian_over_odds"] if direction == "OVER" else forecast["asian_under_odds"]
    matches = []
    for row in ledger:
        if (row.get("source_date") != forecast["fixture_date"] or
                row.get("competition") != forecast["competition"] or
                row.get("fixture") != f"{forecast['home_team']} vs {forecast['away_team']}" or
                row.get("market") != market or row.get("direction") != direction):
            continue
        release_line = row.get("line")
        if release_line is None or abs(release_line - line) > 1e-8:
            continue
        if not no_signal and (row.get("decimal_odds") is None or
                              abs(row["decimal_odds"] - price) > 1e-8 or
                              row.get("stake_u") != 1.0):
            continue
        if no_signal and row.get("state") != "NO_SIGNAL":
            continue
        matches.append(row)
    if len(matches) != 1:
        return "UNLINKED (no unique exact fixture/side/line/price match)"
    row = matches[0]
    if no_signal:
        return "NO SIGNAL (exact fixture/line match; no P&L)"
    if row["state"] == "SETTLED":
        return f"SETTLED: {row['settlement']} ({row['pnl_u']:+.4f}u)"
    return f"{row['state']} (exact quote match)"
