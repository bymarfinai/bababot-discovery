# ETH London -> New York Pre-H2 Retrace — M2 Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Continue only from the supported ETH London->New York M1 structure. Mirror BTC B27W causally and discover whether ETH has a stable native pre-H2 retracement location.

## Frozen cohort
- ETHUSDT perpetual, raw 5m.
- London reference: 08:00-13:30 UTC.
- New York active session: 13:30-20:00 UTC.
- LONG only.
- Reuse exact persisted M1 ETH `K1 OPP0` identities; no new signal detector.
- Historical partitions unchanged: external, development, reference_validation, August telemetry.

## Causal event grammar
1. M1 K1 bar is the first bar of the first distinct London-High touch episode.
2. Consecutive bars with `high >= H` and `close <= H` remain the same K1 episode.
3. A causal leave exists only after a completed bar that no longer qualifies as High touch and has not strict-close broken H or L.
4. Entry eligibility begins on the next raw 5m bar after the leave bar completes.
5. H2 is the first later raw 5m bar with `high >= H`, regardless of close. The H2 bar itself is never entry-eligible.
6. A completed `close < L` before H2 is opposite-break terminal. A bar that simultaneously has `high >= H` and `close < L` is ambiguous terminal and cannot be used as fill or H2 success.
7. If neither terminal occurs, window ends at 20:00 UTC.

## Frozen retracement grid
Measured from London Low=0 to High=1:
- F95 = 0.95
- F90 = 0.90
- F85 = 0.85
- F80 = 0.80
- F75 = 0.75

A level is filled when an eligible pre-terminal 5m bar spans the exact frozen price `L + f*(H-L)`. No bar on/after H2 may fill.

## Outputs
For each partition and each level:
- M1 K1 setup count;
- clean causal windows;
- fills before H2;
- fill rate;
- H2 target-hit count/rate among fills;
- median minutes fill -> H2;
- reward to H in range units;
- median and p10 minimum post-entry fraction;
- median adverse excursion in range units.

Persist window-level and entry-level audit CSVs.

## Frozen discovery screen
A level is `SCREEN_PASS` only if the exact same level satisfies in **each** external, development, and reference_validation:
- at least 30 pre-H2 fills;
- at least 70% H2 target-hit rate among fills.

No level is selected by maximum hit-rate, maximum fill-rate, or any economic metric. If multiple adjacent levels pass, report the full supported family. If none pass, stop and diagnose; do not fine-sweep intermediate fractions post hoc.

## Not tested in M2
No stop, E-target, PF, PnL, fee, slippage, runner, leverage, portfolio lock, clock rotation, alternate session, SHORT, EMA/ATR/volume/regime filter.

## Mandatory assertions
- ETH M1 persisted signal identity is reproduced exactly.
- Every M1 K1 bar reproduces the frozen High-touch condition.
- Entry eligibility never begins before completed causal leave.
- Every filled entry is strictly before terminal/H2 bar.
- Entry price equals its exact range fraction.
- No future terminal event affects pre-terminal eligibility.
- Raw 5m coverage >=99.5%.

Research only. M2 is structural entry discovery, not a tradable strategy.