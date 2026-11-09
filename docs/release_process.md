# P8.1D — Local Public → GitHub Public daily publication

## Boundaries

The Private science system and Local Public remain unchanged. This public repository does not know how to access Private runtimes; its only permitted input is the previously generated **Local Public** `public_data/tracker_snapshot.json`. New data move in one direction. Only the `POST_ACTIVATION_V2` cohort and AH/OU primary markets are released. The transformer manually constructs an explicit public field allowlist, strips internal IDs and rule names, and does not publish raw screenshots, internal ledgers, model files, or private paths.

### One-time initial repository creation

When the public GitHub repository has not yet been created, first complete the Mac security check, tests, and the **separate** `bash scripts/publish_github.sh` first-time release. Do not run a daily `--push` against a non-existent or different GitHub repository.

### Each day's update

1. Record outcomes, and complete your normal **Private → Local Public** publish procedure locally.
2. Preview only (the default):

   ```bash
   cd "$HOME/Projects/football-market-analytics-public"
   conda activate fma-portfolio
   bash scripts/publish_daily_performance.sh --dry-run
   ```

3. Read the changes in signal count, newly settled signals, replacement of earlier NO SIGNAL placeholders, and ROI. **Do not proceed if blocked.**
4. Apply the PUBLIC-only update locally:

   ```bash
   bash scripts/publish_daily_performance.sh --apply
   git diff -- data/public_v2.json data/public_release_manifest.json
   ```

5. When ready and after the public repository has already been created:

   ```bash
   bash scripts/publish_daily_performance.sh --push
   ```

   The script reruns `scripts/security_check.py` and the full tests, then checks the Git branch and exact `origin` repository. It stages only the two allowlisted JSON files. It asks for `PUBLISH` before committing and pushing. No `--force` or automatic model deployment is used. If other staged changes are present, the release stops.

For a different Local Public folder, pass the source explicitly:

```bash
bash scripts/publish_daily_performance.sh --dry-run \
  --snapshot "/full/path/to/public_data/tracker_snapshot.json"
```

## Safety and research integrity

- Each release recomputes ROI from all settled stake and P&L records, not from yesterday's headline number.
- Each existing settled record is verified against independent Asian line settlement arithmetic. A mismatched score, odd, line, or profit **stops** the release.
- Already published real signals cannot silently change their direction, line, stake, or quote and cannot disappear.
- Already published settled results cannot silently be overwritten. Genuine corrections need a reviewed, separate correction workflow with explanation and a new historical revision.
- If an old NO SIGNAL placeholder is superseded by a real forecast for the same fixture/market, the publisher **reports the transition**; it is not misrepresented as a pre-match public timestamp.
- Directories containing Private code, account tokens, source evidence, local binary databases, and backend engines are not included.
- The public source release manifest stores a SHA256 hash and aggregate metrics, never the original Local Public filesystem path. The initial reference metadata are baseline-preparation records, **not** live or pre-kickoff proof.
- Git history preserves ordinary versions but is not a tamper-proof public timestamp; administrators can rewrite branches. Consider branch protection and independent public posting for stronger provenance.

## Tests are now snapshot-agnostic

Initial performance figures are retained in a dedicated **frozen test fixture**, while active-data tests check row identity, settlement correctness, aggregation, and cumulative P&L for every daily release. Thus a legitimate daily update does not trigger a false hardcoded “34 records” failure. Human research claims in `README.md` and `docs/evaluation.md` explicitly refer to the initial sample and should not be presented as the latest statistics.

## Hosting

A Streamlit-hosted portfolio reading this GitHub repository will display the new JSON after code deployment/refresh by the hosting provider. GitHub itself **does not run the Python forecasting engine**. The Mac owner-local worker remains separate and closed to cloud visitors until an authenticated backend has passed the P8.1C deployment and confidentiality checks.
