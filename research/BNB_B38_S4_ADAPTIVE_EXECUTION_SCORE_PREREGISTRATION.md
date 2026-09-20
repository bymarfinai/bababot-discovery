# BNB B38-S4 — Frozen Adaptive Execution Scoring Preregistration

**Scientific identity:** `BNB_B38_S4_ADAPTIVE_EXECUTION_SCORE_V1`

## Purpose

Score the frozen B38-S3 adaptive execution engine without altering:
- parent structural family,
- adaptive entry timing,
- structural invalidation reference,
- structural TP1/TP2/TP3 ladder.

This is a **2022-2024 development execution characterization**, not an OOS validation claim.

## Integrity gate

Before scoring:
- frozen H1-demand / 15m parent = 788;
- adaptive plan ledger = 788;
- ENTRY plans = 690;
- cancelled before reclaim = 98;
- no-trigger = 0.

Any drift aborts scoring.

## Outcome resolution timeframe

Entries and structural objectives are defined on 15m closes, but target/stop ordering is resolved using the exact underlying **5m bars strictly after entry_ts**.

For each target slot independently:

- `WIN`: target high is touched before structural SL low is touched.
- `LOSS`: structural SL low is touched before target high.
- `AMBIGUOUS_SAME_5M`: target and SL are both touched in the same first decisive 5m bar; intrabar order is unknowable.
- `UNRESOLVED`: neither target nor SL is touched before 2024-12-31.

Main hit-rate and R statistics include WIN + LOSS only.
Ambiguous and unresolved are reported separately.

## Separate full-position policies

Three independent frozen objective policies are scored where the target exists:

1. `TP1_FULL_EXIT`
2. `TP2_FULL_EXIT`
3. `TP3_FULL_EXIT`

No partial exits, break-even moves, trailing stops, or target substitution are introduced.

For TP2/TP3, a prior lower target touch does not end the policy. If price later hits SL before the selected target, that selected-target policy is a LOSS.

## R accounting

For each entry:
- structural risk = entry_price - sl_reference;
- target reward = target_level - entry_price;
- target R = reward / structural risk.

Realized R:
- WIN = target R;
- LOSS = -1R;
- ambiguous/unresolved = NaN in main expectancy.

Persist:
- hit rate;
- median and quartiles of winning R;
- mean realized R / trade (expectancy);
- total realized R;
- profit factor = sum winning R / absolute sum losing R;
- max consecutive wins;
- max consecutive losses;
- maximum cumulative-R drawdown in chronological entry order.

This assumes equal **1R risk allocation per signal** and is not a dollar portfolio simulation.

## Breakdowns

Report each target policy:
- pooled;
- by execution mode;
- by 2022 / 2023 / 2024.

Execution modes are frozen:
- IMMEDIATE_CLEAN_RECLAIM
- IMMEDIATE_SWEEP_RECLAIM
- DELAYED_CLEAN_RECLAIM
- DELAYED_SWEEP_RECLAIM

## Sensitivity

Also persist a conservative expectancy sensitivity in which `AMBIGUOUS_SAME_5M` is treated as -1R.
Do not use this sensitivity to change rules.

## Stop rule

Do not:
- alter entry/SL/TP levels after outcomes;
- add buffers;
- skip modes based on results;
- add RR filters;
- add sessions, indicators, derivatives, ATR, volume, or funding;
- invent partial exits or trailing logic;
- use 2025-2026 as OOS validation for B38-S4.
