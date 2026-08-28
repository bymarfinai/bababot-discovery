# B27EW — BNB Session-Native LONG M11 Failed-Before-H Entry Repair Discovery

## Purpose
Development-only discovery aimed specifically at converting existing B27ES/B27EV E5_MICRO_HL_BULL losses into actual net wins. This milestone does not validate or promote a live rule.

## Frozen baseline
- Candidate: E5_MICRO_HL_BULL from B27EO/B27ES.
- Development partition only: 2022-01-01 <= date < 2025-01-01.
- Baseline population integrity: 50 opportunities = 25 net wins + 25 net losses under B27ES best cell.
- TP: H + 0.30R.
- SL: 0.30R below each executed leg entry.
- Total round-trip fee + slippage: 0.15% per executed notional fraction.
- Same-bar TP/SL ambiguity: SL owns the bar.
- Session-close exit if neither barrier is reached.

## Objective
Primary score is **original baseline loss -> actual net-positive opportunity**. No-trades are never counted as conversions. Existing baseline winner retention is reported explicitly.

The main anatomy target is the loss cohort that failed before H, but every intervention is applied to all 50 baseline opportunities so winner damage is observable.

## Preregistered entry-repair interventions
No thresholds will be changed after results are seen.

### Baseline
- BASELINE: unchanged original full-size E5 entry.

### Split-entry repairs
Total planned notional remains 100%; no leverage/notional increase.
- S05: 50% at original E5 entry + remaining 50% as resting buy limit at original entry - 0.05R.
- S10: same, add at -0.10R.
- S15: same, add at -0.15R.
- S20: same, add at -0.20R.
- S25: same, add at -0.25R.

Each leg has the same structural TP H+0.30R and its own SL 0.30R below that leg's fill. If the second leg never fills, only the first 50% is exposed. A second-leg fill on a bar whose open is below the limit uses the more favorable bar open; otherwise the limit price. Each leg is simulated causally from its fill bar with SL-first same-bar ordering.

### Full-entry dip/recovery repairs
These replace the original entry; if the recovery trigger never occurs, the opportunity is NO_TRADE and is not a conversion.
- D10_RECLAIM: after original E5 signal, require price to first trade <= original entry - 0.10R; then require a completed 5m close >= original entry; enter next 5m open.
- D20_RECLAIM: same with a 0.20R adverse dip.
- D10_FRESH_MICROHL: after price first trades <= original entry - 0.10R, require a fresh completed bullish micro higher-low bar (low > previous low, close > previous close, close > open); enter next 5m open.

## Scorecard
For every intervention report:
- original Loss->Win, Loss->Loss, Loss->NoTrade;
- original Win->Win, Win->Loss, Win->NoTrade;
- net-positive opportunities out of 50;
- executed opportunity WR;
- total trade legs;
- average net return per original opportunity;
- illustrative PnL at $500 planned notional;
- opportunity-level profit factor;
- among the 19 known baseline losses that failed before H: converted count.

## Ranking
Rank interventions by:
1. highest original Loss->Win count;
2. highest failed-before-H Loss->Win count;
3. highest original Win->Win count;
4. highest net-positive opportunities;
5. highest average net return per opportunity.

No intervention combination is allowed in B27EW. In particular, do not combine with B27EV partial-at-H/H+0.10 management in this milestone.

## Stop conditions
STOP after development discovery. No external/reference-validation/August reveal, no retuning, no intervention combination, no SHORT/live integration.
