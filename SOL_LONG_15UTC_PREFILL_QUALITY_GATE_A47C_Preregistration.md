# SOL LONG 15UTC Pre-Fill Quality Gate — A47C Preregistration

## Purpose
A47B found one unique replicated causal separator represented by two complementary features:
- `prefill_last_close_distance_H_R` (winner direction: higher), and
- `prefill_last_close_location_R` (exact complementary location representation).

A47C converts only the distance representation into an executable quality gate. No other A47B diagnostic feature is allowed.

## Frozen parent
- A20 `R360 / 15UTC / E0_RESTING_H -> E40` parent.
- Same lifecycle, target, costs, partitions, notional, and outcome accounting.
- A47C does not introduce recovery or change the H entry price.

## Executable gate
At each completed 5m candle after 15:00 UTC, before H has been touched, calculate:

`D = (H - last_completed_close) / R`

The H limit is armed for the immediately following 5m bar only when `D >= T`.
If H is first touched with no completed post-15 candle available, the setup is skipped.

This reproduces the A47B causal boundary: only the candle immediately preceding the frozen first H-touch/fill may authorize that fill. No fill-bar information is used.

## Development-only threshold family
Direction is frozen from A47B: keep higher `D`.
Exactly three deterministic thresholds are derived from Development stress outcomes only:

1. `MIDPOINT`: midpoint between Development WIN median D and FAIL median D.
2. `T55_MAXN`: the smallest observed Development cutoff T such that keeping `D >= T` yields stress WR >=55%, among subsets with N >=200. This is the maximum-N 55% solution.
3. `T60_MAXN`: the smallest observed Development cutoff T such that keeping `D >= T` yields stress WR >=60%, among subsets with N >=150. This is the maximum-N 60% solution.

No neighboring threshold, manual adjustment, OOS threshold selection, or post-hoc target change is permitted.

## Development metrics
For baseline and every candidate report raw and 5bps:
- N, WR, PF, expectancy, net;
- max drawdown;
- max loss streak;
- winner-retention rate versus baseline;
- loser-rejection rate versus baseline.

A threshold is Development-eligible only if:
- N >=200;
- stress WR improves baseline by >=8 percentage points;
- stress PF >= baseline stress PF + 0.15;
- stress expectancy > baseline stress expectancy;
- stress net > 0;
- retains >=40% of baseline stress winners.

Freeze one Development winner in priority order:
1. any eligible candidate with stress WR >=60%, highest N;
2. otherwise eligible candidate with highest stress WR, then highest N;
3. otherwise NONE.

## Frozen OOS validation
Only the frozen Development winner is applied unchanged to External and Reference Validation.
It is OOS-supported only if both partitions satisfy:
- stress WR > their own baseline stress WR;
- stress PF > their own baseline stress PF;
- stress expectancy > their own baseline stress expectancy;
- stress net > 0;
- N >=75;
- winner retention >=35%.

Aspirational success is >=60% stress WR in both OOS partitions, but support does not require forcing that number if the filter materially improves economics and survives both OOS pools.

## Pooled audit
If a winner exists, report the frozen threshold across all three partitions combined, including total retained N, WR/PF/net, max DD, max loss streak, total winner retention, and loser rejection.

## Verdicts
- `SOL_LONG_15UTC_PREFILL_GATE_A47C_SUPPORTED_60PLUS` if OOS-supported and both OOS stress WR >=60%.
- `SOL_LONG_15UTC_PREFILL_GATE_A47C_SUPPORTED_IMPROVEMENT` if OOS-supported but one/both OOS WR <60%.
- `SOL_LONG_15UTC_PREFILL_GATE_A47C_REJECTED_DEVELOPMENT` if no Development candidate qualifies.
- `SOL_LONG_15UTC_PREFILL_GATE_A47C_REJECTED_OOS` if the frozen Development winner fails OOS.

Research only. Live Baba Bot remains unchanged.
