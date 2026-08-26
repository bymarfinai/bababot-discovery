# ETH LONG B27Q-Adapt — Causal Previous-Session Liquidity Pressure Census — Preregistration

## Purpose
Re-run the BTC B27Q structural milestone on ETHUSDT before tuning ETH entry location, stop, target, or runner.

The invariant structural DNA is retained:
completed previous-session range -> first/second/third distinct visit to frozen High -> causal chronology -> observe whether the active session ultimately strict-close breaks High, strict-close breaks Low, or neither.

This experiment is LONG-only. It does not transplant BTC F85, F35, E20, or BTC four-zone portfolio parameters.

## Instrument / data
- ETHUSDT perpetual
- raw completed 5m Binance futures bars
- frozen horizon 2020-01-01 through 2026-08-21, matching the BTC research horizon
- same external / development / reference_validation / August partitions as the existing ETH E1 audit
- weekdays only

## Session transitions retained from the BTC milestone
1. ASIA_TO_LONDON: reference 00:00-08:00 UTC, active 08:00-13:30 UTC
2. LONDON_TO_NEWYORK: reference 08:00-13:30 UTC, active 13:30-20:00 UTC

These clocks are treated as the first structural milestone, not assumed final ETH habitat. Clock adaptation belongs to later milestones if the structural cohort survives.

## Frozen event semantics
- H = completed previous-session High; L = completed previous-session Low; require H > L.
- A strict close > H is HIGH breakout; a strict close < L is LOW breakout.
- A High visit requires high >= H and close <= H before any strict breakout.
- Consecutive High-touch bars are one visit episode. A later High touch after leaving is a new distinct visit.
- A 5m bar that touches both H and L before breakout is chronologically ambiguous and that session is rejected.
- K in {1,2,3} means the distinct High visit number.
- OPP0 means zero distinct Low visits have occurred before that High signal.
- Signal time is the completion of the 5m High-visit bar.

## Candidate grid
For each transition and partition report LONG cohorts for:
- K1 / K2 / K3
- ALL purity
- OPP0 purity

No retracement entry level is tested here.

## Structural outputs
For every transition x partition x K x purity:
- N signals
- target High-break count/probability
- opposite Low-break count/probability
- no-break count/probability
- median minutes from signal to terminal breakout when a breakout occurs

Persist one-row-per-visit and one-row-per-signal audit files.

## Structural screen for the next milestone
A cohort may advance to ETH B27W-Adapt only if the exact same transition/K/purity has, in external, development, and reference_validation:
- N >= 30 in each partition;
- target High-break probability >= 70% in each partition;
- opposite Low-break probability <= 20% in each partition.

If multiple cohorts pass, rank by:
1. highest minimum target-break probability across the three major partitions;
2. then highest total N;
3. then lower K;
4. then OPP0 over ALL if otherwise tied.

This selection rule is frozen before observing the ETH B27Q-Adapt result.

## Guardrails
- No F85/F80/etc entry tuning in this milestone.
- No stop/TP/runner tuning.
- No EMA/ATR/volume/regime/body/wick filters.
- No validation-driven clock changes inside this milestone.
- No live or production changes.

Research only.