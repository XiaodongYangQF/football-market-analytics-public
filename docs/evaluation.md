# Evaluation protocol

## Performance definition

For a set of settled records \(i=1,\ldots,n\) with nominal stakes \(s_i\) in units and signed net settlement P&L \(\pi_i\):

\[
\mathrm{Weighted\ ROI}=100\,\frac{\sum_i\pi_i}{\sum_i s_i}\,\%.
\]

`NO SIGNAL`, `NOT_RECORDED` and pending/unavailable records are **not** treated as losses or entered into the invested stake. A push counts as 1u turnover and zero P&L.

If a hypothetical real stake were **€20 per 1u**, the initial +3.8000u would correspond to +€76 of simulated net P&L, over €680 cumulative stakes. This is **not a bankroll return** or a record of real wagers.

## Initial snapshot checks

- Curated Public V2 rows: **67**, of which **34 settled**, **31 NO SIGNAL**, **2 NOT_RECORDED**.
- Settled records relate to **24** distinct fixture keys.
- Nominal turnover: **34u**; simulated P&L: **+3.8000u**; ROI: **+11.17647%**.
- AH: **17 signals, −0.3875u**; OU: **17 signals, +4.1875u**.
- Outcomes: **15 full wins**, **4 half-wins**, **2 pushes**, **3 half-losses**, **10 full losses**.

All figures can be recalculated by [`fma_portfolio/metrics.py`](../fma_portfolio/metrics.py). The public [`fma_portfolio/settlement.py`](../fma_portfolio/settlement.py) independently reproduces all 34 recorded outcomes and profits from public market, line, side, quote, and 90-minute score fields. The upstream audit compared recorded scores/odds/handicap settlement arithmetic; it was not an independent bookmaker execution audit.

## Statistical interpretation

The observed ROI is **exploratory and preliminary**. Only 34 market signals are settled, with some AH and OU outcomes correlated within a common fixture. Cross-competition differences are unstable. In the source review, positive profits were highly concentrated in La Liga; the other leagues combined were close to zero. No statistically established advantage over market prices is claimed.

Future validation should:

1. Accumulate all eligible cases under an unchanged, documented policy, including NO SIGNAL.
2. Report outcome quality, price provenance and executable-vs-exploratory quotes separately.
3. Build market-only benchmarks and, where model probabilities exist, proper scoring rules and calibration analyses.
4. Report uncertainty with fixture-cluster-aware methods, not treat same-fixture AH and OU as independent.
5. Publish a sequence of fixed historical releases rather than rewriting unsuccessful periods.

## Evidence and reproduction boundary

- **Reproducible here:** curated data transformation from the saved Local Public snapshot, deterministic P&L summaries, sample counts and dashboard output.
- **Not publicly reproducible here:** reconstruction of the underlying Private model's forecasting rule decisions from raw pre-match market inputs. That requires the frozen, deliberately undisclosed engine.
- **Not claimed:** verified real-time availability of quotes, independent external audit of every original price, or actual real-money ROI.

The source date column is intentionally labeled **source fixture date**, because some source calendar dates were not yet reconciled against official schedule references at the initial export. This caveat does not affect summed P&L but matters for date-based reporting.
