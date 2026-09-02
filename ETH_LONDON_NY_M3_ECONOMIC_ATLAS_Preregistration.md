# ETH London -> New York M3 Economic Atlas — Preregistration

## Purpose
Convert the frozen M2 pre-H2 retracement family into actual trading economics before drawing any conclusion about which F-level is best.

This experiment preserves the M1/M2 causal grammar:
London 08:00-13:30 UTC -> New York 13:30-20:00 UTC -> LONG K1 OPP0 -> contiguous first High-touch episode -> completed causal leave -> pre-H2 limit entry only.

## Frozen entry levels
Evaluate exactly the M2 grid:
- F95 = L + 0.95R
- F90 = L + 0.90R
- F85 = L + 0.85R
- F80 = L + 0.80R
- F75 = L + 0.75R

Entry identities/timestamps must reproduce M2 exactly. No new confirmation/filter is introduced.

## Frozen breakout targets
H2 remains a milestone, not TP. Test only:
- E10 = H + 0.10R
- E15 = H + 0.15R
- E20 = H + 0.20R

## Frozen invalidation distances
To compare the five entries on equal risk geometry, test only close-confirmed boundaries measured below each entry:
- D30: entry_fraction - 0.30R
- D40: entry_fraction - 0.40R
- D50: entry_fraction - 0.50R
- D60: entry_fraction - 0.60R

Examples: F95/D30 -> F65 boundary; F85/D50 -> F35 boundary; F75/D60 -> F15 boundary.

Invalidation occurs only when a completed raw 5m candle closes strictly below the frozen boundary. Wick-only penetration does not exit. Exit price is that actual close.

## Chronology
1. Position is active from the exact M2 limit fill bar.
2. On the fill bar itself, only completed-close invalidation can occur after the intrabar fill.
3. Starting from the next raw 5m bar, target limit is checked intrabar; if high >= target, TP fills at target.
4. On the same later bar, target touch takes precedence over a close invalidation because the close is only knowable at bar completion.
5. If no TP/invalidation by New York end, exit at the first available 5m open at/after 20:00 UTC.
6. H2 alone never closes the trade.

## Economics
- illustrative notional: $500
- round-trip fee: $0.40
- trading win: net PnL > 0

Primary execution: 0 bps.
Stress execution: 5 bps adverse entry and adverse market exit; resting target remains exact target price.

## Grid
Exactly 5 entries x 3 targets x 4 invalidation distances = 60 cells. No intermediate F-level, target, stop distance, timing, filter, runner, or leverage variation is allowed after results are visible.

## Reporting
For every partition/cell and pooled-major report:
- N, WR, PF, expectancy, net, max loss streak
- TP / close-invalidation / time-exit counts
- median winner/loser, median hold
- 5bps WR/PF/expectancy/net

Also provide per-entry best-observed WR cell for descriptive comparison only.

## Frozen robustness screen
A cell is `SCREEN_PASS` only if the exact same entry/target/invalidation combination has in external, development, and reference_validation:
- >=30 trades in each partition
- WR >=70%
- PF >=1.20
- positive expectancy and net
and pooled 5bps PF >1 with positive net.

This screen intentionally means a sparse level such as F95 may have attractive observed WR but cannot be formally promoted if a major partition has <30 fills.

## Decision hierarchy
1. Do not conclude from M2 H2 hit rate.
2. Among `SCREEN_PASS` cells, primary ranking is pooled-major actual trading WR.
3. Ties/near-ties are resolved by PF, then expectancy, then 5bps robustness.
4. If no cell passes, report no supported economic winner even if a descriptive pooled WR leader exists.
5. Do not tune a runner or portfolio lock in M3.

Historical partitions have already been inspected; this is structural/economic calibration, not pristine unseen OOS validation.
