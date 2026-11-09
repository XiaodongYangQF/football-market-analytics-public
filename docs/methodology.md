# Methodology: observable outputs, not proprietary rules

## Information and prediction pipeline

The underlying private research workflow consumes market inputs captured from **pre-match** information, applies a fixed decision policy, stores a forecast and can later evaluate it against the observed result.

This repository deliberately begins **after** that process, from a curated Local Public release. It does not include the proprietary scientific engine or disclose the conditions that create or reverse individual trading signals. It cannot independently generate a new forecast.

Replaying a historically observed pre-match quote through a fixed model can be useful for studying predictive performance even if the model invocation is later. This is not identical to proving the forecast was published before kickoff, nor does it establish that a quoted price remained executable. Those distinct claims should not be conflated.

## Markets

**AH (Asian Handicap)** evaluates the selected side against an adjusted goal difference. **OU (Asian Total)** evaluates total goals against a quoted line. Quarter-lines split a stake into two equal half-line components and can therefore generate half-wins and half-losses. Each published settled forecast carries one nominal unit of stake.

For a decimal quote `o` and stake `s`, simulated P&L is determined by the saved result's settlement category: full win `s × (o−1)`, half win `s × (o−1)/2`, push `0`, half loss `−s/2`, loss `−s`. The repository reports the settlement derived upstream and provides transparent metric aggregation; it does not silently invent missing quotes or settlements.

## Public V2 dataset

The initial data are sourced from the user-provided **Local Public** snapshot of 8 November 2026, filtered to `POST_ACTIVATION_V2`. The release includes a fixed allowlist of public-facing fields: source fixture date, competition, fixture, market, forecast direction, line, decimal odds, nominal stake, final score, settlement state, simulated P&L, and price-evidence classification.

It explicitly excludes: Private analysis or trade IDs, internal rule identifiers, full strategy metadata, server or user paths, credentials, account details, raw model inputs and full historical ledgers. No retrospective V2 replays or earlier Public V1 results are combined into the headline.

## Market quotation quality

In the initial snapshot, AH's settled entries are classified as frozen execution quotes, whereas OU entries use exploratory main-line quotes. An exploratory quote is not evidence of a real tradeable offer at a decision instant, so results must be described as simulated settlement rather than actual trading performance.

## No-signal handling

`NO SIGNAL` means the saved Public result contains no direction at that market and carries no stake. `NOT_RECORDED` also carries no stake. Both are kept visible to avoid presenting only successful or actionable selections. They do not enter the ROI denominator.
