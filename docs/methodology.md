# Methodology: observable outputs, not proprietary rules

## Information and prediction pipeline

The underlying private research workflow consumes market inputs captured from **pre-match** information, applies a fixed decision policy, stores a forecast and can later evaluate it against the observed result.

This repository deliberately begins **after** that process, from a curated Local Public release. It does not include the proprietary scientific engine or disclose the conditions that create or reverse individual trading signals. It cannot independently generate a new forecast.

Replaying a historically observed pre-match quote through a fixed model can be useful for studying predictive performance even if the model invocation is later. This is not identical to proving the forecast was published before kickoff, nor does it establish that a quoted price remained executable. Those distinct claims should not be conflated.

## Markets

**AH (Asian Handicap)** evaluates the selected side against an adjusted goal difference. **OU (Asian Total)** evaluates total goals against a quoted line. Quarter-lines split a stake into two equal half-line components and can therefore generate half-wins and half-losses. Each published settled forecast carries one nominal unit of stake.

For a decimal quote `o` and stake `s`, simulated P&L is determined by the saved result's settlement category: full win `s × (o−1)`, half win `s × (o−1)/2`, push `0`, half loss `−s/2`, loss `−s`. The repository reports the settlement derived upstream and provides transparent metric aggregation; it does not silently invent missing quotes or settlements.

## Unified historical research dataset (P8.2H)

The dashboard contains two **separately preserved source assets**, but presents a
single public AH/OU research ledger:

1. `data/historical_replay.json`: a manually curated, allowlisted set of 68
   previously archived, settled AH/main-line OU observations on 48 fixtures.
   Source fixture dates precede the recorded Public V2 window. The public
   interpretation reverses AH-A and OU-B directions at the saved opposing-side
   quote; AH-B, AH-C and OU-A retain their original direction. The economics
   motivate this normalization, but because the sample was available during
   rule development it is **retrospective**, not independently prospective.
2. `data/public_v2.json`: the ordinary Local Public V2 performance release,
   updated through the existing conservative daily publisher. Its original
   initial snapshot has 67 market rows, including 34 settled signals, 31
   explicit NO SIGNAL rows and 2 NOT_RECORDED rows on 33 tracked fixtures.

The initial public combined snapshot includes **81 tracked fixtures** and
**102 settled 1u signals**, giving **+22.9125u simulated P&L and +22.46% ROI**.
Of these 81 tracked fixtures, 72 contain a settled trade. The dashboard does
not show an artificial period split, but this paragraph states the research
provenance honestly. This portfolio does **not** claim that the entire combined
history is pre-registered, out-of-sample or previously published before kickoff.

**Combination algorithm:** published Local Public rows take precedence if the
same date/league/fixture/market exists in a historical replay. Other archived
rows are included once. Two actual recorded public quote observations at
separate lines on the same fixture-market are **two 1u positions**, not a
technical duplicate; both remain in the P&L. Historical Fixed 2.5 calibration
quotes are not treated as a third settled market. The historical input and its
post-processing are reconciled against generic Asian quarter-line settlement
math before a record is curated. The static history file is never overwritten
by the daily update process.

**Missing-data distinction:** an archived fixture with no record for AH or OU
has missing market evidence (`—`). This is not proof that the model generated
`NO SIGNAL`. Actual Local Public NO SIGNAL/NOT_RECORDED states remain intact.

All released records use the same strict public fields: source fixture date,
competition, fixture, market, final forecast side, selected line and decimal
odds, simulated stake, final score, settlement, P&L and an evidence class.
Private analysis IDs, private decision conditions, account data, saved paths,
secrets, and actual trading execution are not published. Quotes are not
independently certified as real-time executable offers; source dates should
not be interpreted as verified kickoff timestamps.

## Market quotation quality

In the initial snapshot, AH's settled entries are classified as frozen execution quotes, whereas OU entries use exploratory main-line quotes. An exploratory quote is not evidence of a real tradeable offer at a decision instant, so results must be described as simulated settlement rather than actual trading performance.

## No-signal handling

`NO SIGNAL` means the saved Public result contains no direction at that market and carries no stake. `NOT_RECORDED` also carries no stake. Both are kept visible to avoid presenting only successful or actionable selections. They do not enter the ROI denominator.
