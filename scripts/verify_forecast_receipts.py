#!/usr/bin/env python3
"""Check each mirrored receipt against CURRENT Github Issue body and provider timestamp.

This detects current changes but cannot prove an issue was never edited earlier.
Read-only operation: does not modify an Issue or repo content.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fma_portfolio.prematch_receipts import ReceiptError, REPO, read_receipts, stamp, batch_from_issue_body, body_for_issue
from scripts.publish_prematch_receipt import _gh_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Latest N only; default all")
    args = parser.parse_args()
    try:
        receipts = read_receipts(ROOT)
        for item in receipts[:args.limit] if args.limit else receipts:
            issue = _gh_json(f"repos/{REPO}/issues/{item['github_issue_number']}")
            if issue.get("body") != body_for_issue(item["batch"]):
                raise ReceiptError(f"Issue content changed: {item['github_issue_url']}")
            if stamp(issue.get("created_at")) != item["github_created_at_utc"]:
                raise ReceiptError(f"Issue server-created timestamp mismatch: {item['github_issue_url']}")
            if batch_from_issue_body(issue["body"]) != item["batch"]:
                raise ReceiptError(f"Issue forecast mismatch: {item['github_issue_url']}")
            print(f"PASS {item['github_issue_url']} | {item['publication_class']}")
        print(f"VERIFIED CURRENTLY: {len(receipts[:args.limit] if args.limit else receipts)} receipt(s)")
    except ReceiptError as exc:
        print(f"VERIFICATION STOPPED: {exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
