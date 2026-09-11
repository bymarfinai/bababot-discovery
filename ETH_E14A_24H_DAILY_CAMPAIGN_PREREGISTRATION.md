# ETH E14A — 24H Daily Campaign Aggregation Preregistration

**Status:** Development-only. OOS CLOSED. Research/shadow only. No live authorization.

## Research question
Temporarily treat all 24 E12 hourly representative LONG characters as eligible signal sources and test whether aggregating them into one fixed-budget daily LONG campaign can improve the full economics+risk package without casually sacrificing win rate.

This experiment does **not** relabel E12 FAIL hours as formal PASS. It is an execution-architecture stress test under the user's explicit temporary assumption that all 24 hourly potentials may contribute to one day campaign.

## Frozen source signals
Use the exact 24-hour representative map from E13C/E12:
- same hourly rule
- same lookback
- same causal quarter-hour anchors (:00/:15/:30/:45)
- Development period only (2022/2023/2024)
- ETHUSDT 5m
- no lookahead

Native E12 holds are **not** used as exits in E14A because the unit of analysis is intentionally changed from independent hourly trades to one daily campaign. E14A uses a fixed daily campaign close described below. E12/E13 results remain untouched.

## Campaign day
A campaign day runs from **23:00 WIB inclusive to next-day 23:00 WIB exclusive**.

All eligible signals inside that 24h window may be used as tranche entries according to the frozen architecture. Every campaign is force-closed at the next 23:00 WIB boundary so campaigns never overlap and total budget remains capped.

If a campaign day has no valid signal, no trade is recorded for that day.

## Capital and fee normalization
- Maximum total campaign notional: **$500**.
- For max-entry architecture `k`, each tranche has fixed notional `$500 / k`.
- Unused tranche capacity remains cash; no retrospective reallocation.
- Prior E12 fee normalization is $0.75 per $500 notional, therefore frozen proportional campaign fee rate = **0.0015 × tranche notional** round-trip equivalent.
- Multiple entry architectures may not exceed $500 aggregate notional.
- No leverage increase, martingale, or loss-triggered size escalation.

## Entry architectures
Evaluate max entries `k ∈ {1,2,3,4}` under three causal policies. This yields 12 labelled cells; the three k=1 cells are expected controls and may be numerically identical.

### SEQUENTIAL_ANY
- First valid signal opens tranche 1.
- Every later valid signal adds the next equal tranche until k is reached.
- Same-hour repeated anchors may add tranches.

### PRICE_IMPROVEMENT
- First valid signal opens tranche 1.
- A later signal may add only when its entry price is **strictly below** the current weighted-average entry price.
- Signal validity is still required; price decline alone cannot add exposure.
- No martingale sizing: tranche size remains fixed.

### DISTINCT_HOUR_CONFIRM
- First valid signal opens tranche 1.
- A later signal may add only if its source WIB hour has not already contributed a tranche in that campaign.
- Price may be above or below current weighted average.
- This tests independent hourly-character confirmation / pyramiding rather than blind averaging.

## Exit and PnL
Every accepted tranche exits at the campaign close price at next 23:00 WIB.

For each tranche:
`gross_pnl = tranche_notional × (exit_price / entry_price - 1)`

`net_pnl = gross_pnl - proportional_fee`

Campaign PnL is the sum of tranche net PnLs. Campaign WR is measured at the campaign level (`campaign_net > 0`).

## Metrics
For every architecture report:
- campaign N
- campaign WR
- total net PnL
- expectancy per campaign
- PF
- max drawdown on sequential campaign equity
- max loss streak / max win streak
- 2022 / 2023 / 2024 N, WR, net, expectancy, PF
- minimum yearly expectancy
- number of years WR >=55%
- average / median entries per campaign
- distribution of 1/2/3/4-entry campaigns
- average deployed notional and capital-utilization rate
- average weighted entry price improvement versus first entry
- average time from first entry to campaign close
- source-hour contribution / acceptance counts

## Frozen daily-campaign baseline
The causal `SEQUENTIAL_ANY, k=1` result is the primary E14A baseline because E14A changes the exit unit to a daily campaign and therefore is not apples-to-apples with E13C's native-hold baseline.

E13C/E13D remain context references only.

## Robust gate
An architecture is `ROBUST` only if:
- N >= 500 campaigns
- pooled WR >=55%
- pooled net >0
- pooled expectancy >0
- pooled PF >=1.20
- pooled max loss streak <=10
- each year N >=150
- each year WR >=52%
- each year net >0
- each year expectancy >0
- each year PF >=1.05
- at least 2/3 years WR >=55%

No threshold may be relaxed after seeing results.

## WR-preservation rule
A multi-entry candidate cannot be called an execution improvement if its pooled campaign WR is below the k=1 baseline WR. It may still be reported as a trade-off candidate.

## Strict Pareto versus k=1 baseline
A candidate is `STRICT_PARETO_IMPROVER` only if all are true:
- WR >= baseline WR
- net >= baseline net
- expectancy >= baseline expectancy
- PF >= baseline PF
- DD <= baseline DD
- max loss streak <= baseline max loss streak
- at least one of these is strictly better
- candidate passes ROBUST gate

## Ranking among ROBUST WR-preserving candidates
Rank in this frozen order:
1. minimum yearly expectancy descending
2. number of years WR >=55% descending
3. pooled expectancy descending
4. pooled PF descending
5. pooled WR descending
6. DD ascending
7. max loss streak ascending
8. net PnL descending
9. lower max-entry count
10. policy name

## Scientific constraints
- Development-only; OOS remains closed.
- No post-result rule rescue or gate relaxation.
- No hourly-character re-selection after result.
- No TP/SL optimization inside E14A.
- No leverage or notional expansion beyond $500 per campaign.
- Do not interpret higher WR alone as superiority if PF, expectancy, DD, loss clustering, or era stability deteriorate.
