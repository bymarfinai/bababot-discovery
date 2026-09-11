# ETH Native London->New York Breakout Confirmation Discovery — Z3 Preregistration

## Purpose
Discover, after the Z2 shallow retest zone, **how far above the frozen reference High ETH must close before the breakout can be considered structurally established**.

This milestone answers only:

> After a causal High K1 OPP0 touch, completed leave, and completed shallow retest in the Z2 F90-F95 zone, what is the furthest completed-close breakout threshold that remains robust across development and both historical holdouts?

This is structural breakout discovery only. It is **not** an entry rule, TP/SL test, PnL backtest, leverage test, or live promotion.

## Frozen upstream lineage
- Z1 clock remains frozen: reference **18:30-00:00 WIB**, execution **00:00-06:30 WIB**.
- Reference duration = 5h30 / 66 raw 5m bars.
- Execution duration = 6h30 / 78 raw 5m bars.
- LONG High-pressure side only.
- Z2 showed that the only development retest candidates were the shallow **F95 and F90** region, while exact F95 did not independently replicate as a final point.
- Therefore Z3 freezes **both F95 and F90 cohorts**. Z3 may not select one retest point over the other.

No clock rescan and no deeper F85/F80 inheritance is allowed.

## Data and partitions
- ETHUSDT Binance Futures raw 5m only.
- Same coverage and partitions as the upstream London->NY research.
- Major partitions: `external`, `development`, `reference_validation`.
- Require raw 5m coverage >=99.5%.
- Require exact 66-bar reference + 78-bar execution windows and weekday execution start.

## Frozen structural chronology
For each session:
1. `H=max(high)` and `L=min(low)` over the completed reference window; require H>L.
2. Reuse Z2 High K1 / OPP0 identity exactly.
3. Reuse the contiguous K1 touch episode and completed causal leave exactly.
4. Retest eligibility begins only on the immediately following raw 5m bar after leave.
5. Freeze two retest cohorts independently: F95 and F90, where `Fxx = L + fraction*(H-L)`.
6. A retest is credited only on a completed, non-terminal bar. A same-bar retest plus breakout is forbidden.
7. Breakout search starts on the raw 5m bar immediately after the completed retest bar.

## Completed-close breakout grid
Let `R = H-L`.

Freeze the following upside completed-close thresholds:
- `B00`: first completed 5m close strictly `> H`.
- `B025`: close `>= H + 0.025R`.
- `B050`: close `>= H + 0.050R`.
- `B075`: close `>= H + 0.075R`.
- `B100`: close `>= H + 0.100R`.
- `B125`: close `>= H + 0.125R`.
- `B150`: close `>= H + 0.150R`.
- `B175`: close `>= H + 0.175R`.
- `B200`: close `>= H + 0.200R`.

These are structural confirmation thresholds, not profit targets.

Also record the first later High arrival (`high >= H`) descriptively, but High arrival is **not selectable** as a confirmed breakout because it does not require a completed close outside the range.

## Terminal-first chronology after retest
Starting on the first raw bar after the completed retest:
1. if `close < L` before a threshold is reached, that threshold outcome is `OPPOSITE_BREAK_BEFORE_THRESHOLD`;
2. otherwise credit every threshold reached by that completed close;
3. a threshold becomes known only at the bar close (`bar_start + 5m`);
4. thresholds already reached remain reached even if price later reverses;
5. if neither threshold nor opposite close-break occurs by execution end, outcome is `NO_THRESHOLD_BY_END`.

No threshold can be credited on the retest bar itself.

## Outputs
For every retest cohort (F95/F90), threshold, and partition report:
- retest cohort N;
- threshold reaches;
- opposite close-breaks before threshold;
- unresolved/no-threshold cases;
- threshold reach rate = reach/N;
- resolved upside rate = reach/(reach+opposite);
- Wilson 95% lower bound of threshold reach rate;
- median minutes retest -> threshold;
- first-High-arrival rate and timing (descriptive).

Persist one row per retest-cohort/threshold/session with timestamps.

## Development candidate gate
Selection sees **development only**.

A threshold is a development candidate only if, for **both F95 and F90** independently:
- >=50 retest cases;
- threshold reach rate >=55%;
- resolved upside rate >=85%;
- threshold reaches > opposite breaks.

Among development candidates, choose the **furthest extension threshold**. This rule is frozen before holdout inspection.

## Historical replication gate
The selected development threshold is supported only if, in **both external and reference_validation**, and for **both F95 and F90** independently:
- >=30 retest cases;
- threshold reach rate >=50%;
- resolved upside rate >=85%;
- threshold reaches > opposite breaks.

No pooled rescue is allowed.

## Mandatory assertions
1. Z1 clock provenance matches the frozen 18:30->00:00 WIB clock.
2. Z2 scanner is rerun deterministically and produces F95/F90 retest cohorts.
3. No breakout threshold timestamp is on or before the completed retest timestamp.
4. B00 requires strict completed close >H.
5. B025-B200 prices equal H plus the frozen range extension exactly.
6. Threshold reach counts are monotonic non-increasing as extension increases for each cohort/partition.
7. F90 retest sessions are a subset of F95 retest sessions.
8. Holdouts are not used to choose the development threshold.
9. No entry, TP, SL, fee, leverage, PnL, PF, expectancy, or live-rule output is produced.

Research only. Stop after Z3.