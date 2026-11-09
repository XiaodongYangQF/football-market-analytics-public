# P8.1E — Public GitHub prematch receipts

## Separate the two datasets

- **P8.1D:** Public V2 historically recorded and subsequently settled Local Public performance ledger; refreshed once per day. Some forecasts were replayed from archived prematch quotes and are **not** independently pre-kickoff public publication.
- **P8.1E:** A new forward-looking provenance dataset: the unchanged model's P7.4 output is uploaded to a PUBLIC GitHub Issue **before the declared kickoff**. Each issue contains a canonical JSON payload and SHA-256, with GitHub server-assigned `created_at`. The identical payload is mirrored in `data/forecast_receipts/*.json` and displayed by the public Streamlit Portfolio.

Do not combine both populations as if the retrospective historical cohort had been prospectively publicly posted.

## Data lifecycle

1. Generate model forecasts in existing owner-local UI. Save the source P7.4 record(s) and export the UI's JSON archive.
2. Review one carefully scoped batch of 1–16 fixtures **all scheduled for the same UTC kickoff**; explicitly supply accurate kickoff UTC and relevant selectors. The current source schedule contains dates but does not verify kickoff times independently.
3. Default CLI preview is offline/read-only. For confirmed publication, `--publish` checks the GitHub repository, branch, commit state, public visibility, Issues availability, local forecast creation time and duplicate records.
4. Create the public GitHub Issue *first*. Use GitHub REST response's UTC `created_at`; never backdate a commit or infer publication time from local file metadata. Compute `ON_TIME_DECLARED` if and only if `created_at < user-declared kickoff`. A late response is marked `LATE_PUBLICATION`.
5. Store a strict-schema JSON mirror with the actual GitHub server timestamp, URL, full inputs/outputs and SHA-256; commit/push only that specific file to `main`. If pushing fails after the Issue has been created, use `--resume-issue N` or push the existing commit; never create a second issue.
6. The Portfolio `Pre-match archive` displays records independently. It attempts a read-only **exact-quote** match to the P8.1D settlement ledger; unmatched data remain unlinked and are not incorporated into simulated P&L.

## Provenance limitations

- The provider timestamp proves that an Issue was created at a given time, **not** that the kickoff supplied by the user is official, not that the quote existed at that instant or could be executed, and not that all predictions generated were published. There is no independent quote screenshot or bookmaker audit in P8.1E.
- Issue bodies can be edited/deleted by authorized users. `verify_forecast_receipts.py` retrieves the current body and checks it against the originally mirrored canonical hash, but does not provide irreversible notarization or full historical edit detection. Git history can also be rewritten by privileged users. Stronger evidence requires server-side append-only storage, signed proofs, independent archives or third-party auditing.
- Source P7.4's `saved_at_utc` is a local application timestamp, not GitHub's publish time. A prediction recorded *after kickoff* is rejected; the public label is governed by **GitHub created_at**.
- No actual wager is placed, the listed prices may not have been executable, and a receipt is not an actual trade blotter.
- The archive may be selectively published; completeness and absence of discretionary selection must be separately audited.

## Operational documents

See `P8_1E_PREMATCH_RECEIPTS.md` for complete Mac installation, CLI examples, public-repo prerequisite, resume behavior and daily settlement synchronization.
