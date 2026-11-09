#!/usr/bin/env python3
"""Pre-publication guard for curated data and accidentally included private files."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fma_portfolio.release import validate_release
from fma_portfolio.daily_publish import make_manifest, MANIFEST_SCHEMA
from fma_portfolio.prematch_receipts import read_receipts, ReceiptError
from fma_portfolio.eligibility import load_policy, EligibilityPolicyError

FORBIDDEN_DIR_NAMES = {
    "runtime_data", "private_data", "freezes", "backups", ".git",
    ".claude", ".agents", "__MACOSX", "logs", "evidence", "storage", "core", "backend"
}
FORBIDDEN_SUFFIXES = {".zip", ".sqlite", ".db", ".pem", ".key", ".p12"}
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{15,}"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "API credential assignment": re.compile(r"(?im)^\s*(?:API_KEY|SECRET_KEY|ACCESS_TOKEN|PASSWORD)\s*=\s*(?![\"']?example\b)[^\s#]{12,}"),
}


def run() -> list[str]:
    failures = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in {"__pycache__", ".pytest_cache", ".venv", ".git"} for part in relative.parts):
            continue
        if any(part in FORBIDDEN_DIR_NAMES for part in relative.parts[:-1]):
            failures.append(f"Forbidden directory: {relative}")
        if path.name.startswith(".env") or path.name == "secrets.toml" or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(f"Forbidden file: {relative}")
        if path.stat().st_size > 2_000_000:
            failures.append(f"Unexpected large file: {relative}")
        if path.suffix.lower() in {".py", ".md", ".yml", ".yaml", ".toml", ".json", ".txt", ".sh"}:
            content = path.read_text(encoding="utf-8", errors="replace")
            for name, pattern in SECRET_PATTERNS.items():
                if pattern.search(content):
                    failures.append(f"Potential {name}: {relative}")
    # P8.1C-2 baselines/corpora contain private model inputs and must NEVER
    # enter the GitHub portfolio, even if somebody renamed the JSON file.
    private_evidence_schemas = {
        "FMA_PRIVATE_RUNTIME_PARITY_CASES_V1",
        "FMA_PRIVATE_RUNTIME_PARITY_BASELINE_V1",
        "FMA_PRIVATE_RUNTIME_PARITY_REPORT_V1",
        "FMA_PRIVATE_ELIGIBILITY_COVERAGE_V1",
    }
    for path in ROOT.rglob("*.json"):
        if any(part in {"__pycache__", ".git", ".pytest_cache", ".venv"}
               for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file() and path.stat().st_size <= 2_000_000:
            try:
                private_schema = json.loads(path.read_text(encoding="utf-8")).get("schema")
            except (OSError, AttributeError, ValueError, UnicodeError):
                continue
            if private_schema in private_evidence_schemas:
                failures.append(f"Private parity evidence must never be committed: {path.relative_to(ROOT)}")
    # Ensure the published coverage policy is present and internally consistent.
    try:
        load_policy()
    except EligibilityPolicyError:
        failures.append('Missing or invalid public eligibility policy')
    data_path = ROOT / "data" / "public_v2.json"
    try:
        obj = json.loads(data_path.read_text(encoding="utf-8"))
        validate_release(obj)
        for row in obj["records"]:
            for field in ("source_date", "competition", "fixture", "direction"):
                if not row[field] or not isinstance(row[field], str):
                    failures.append("Invalid public row text value")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        failures.append(f"Invalid public data release: {exc}")
    manifest_path = ROOT / "data" / "public_release_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected_keys = {
                "schema", "released_at_utc", "source_public_snapshot_sha256", "records_sha256",
                "row_count", "settled_signals", "no_signal_rows", "not_recorded_rows",
                "pending_rows", "turnover_u", "pnl_u", "roi_pct", "note",
            }
            if set(manifest) != expected_keys or manifest["schema"] != MANIFEST_SCHEMA:
                failures.append("Invalid release manifest schema")
            else:
                from datetime import datetime
                datetime.fromisoformat(manifest["released_at_utc"].replace("Z", "+00:00"))
                digest = str(manifest["source_public_snapshot_sha256"])
                if not re.fullmatch(r"[a-f0-9]{64}", digest):
                    failures.append("Invalid source snapshot SHA256")
                base = make_manifest(obj, digest, released_at_utc=manifest["released_at_utc"])
                for field in (
                    "records_sha256", "row_count", "settled_signals", "no_signal_rows",
                    "not_recorded_rows", "pending_rows", "turnover_u", "pnl_u", "roi_pct",
                ):
                    if manifest[field] != base[field]:
                        failures.append(f"Manifest does not reconcile with public data: {field}")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            failures.append(f"Invalid release manifest: {exc}")
    try:
        # Strict allowlist schemas, canonical hashes, unique fixtures, GitHub-only links.
        read_receipts(ROOT)
    except (ReceiptError, OSError, ValueError, KeyError, TypeError) as exc:
        failures.append(f"Invalid public prematch receipt archive: {exc}")
    return failures


if __name__ == "__main__":
    errors = run()
    if errors:
        print("SECURITY CHECK FAILED")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)
    print("SECURITY CHECK PASS: no forbidden files, credentials or unexpected data fields")
