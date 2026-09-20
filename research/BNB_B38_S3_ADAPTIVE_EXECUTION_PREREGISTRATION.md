# BNB B38-S3 — Adaptive Execution State Machine Preregistration

**Scientific identity:** `BNB_B38_S3_ADAPTIVE_EXECUTION_V1`

## Purpose

Convert the frozen B38-S2 H1-demand / 15m structural archetypes into one causal adaptive execution engine.

The structural principle stays common:

`H1 bullish BOS -> causal H1 demand -> 15m expansion -> corrective return -> demand interaction -> reclaim state`

Entry, structural invalidation, and target objectives adapt to the observed reclaim state.

This phase freezes execution logic and measures only its structural geometry. It does **not** optimize or score trade profitability.

## Parent population

Frozen B38-S1 / B38-S2 development family:
- H1 demand
- 15m execution
- 2022-01-01 through 2024-12-31
- N = 788

## First-touch archetypes

A. CLEAN_PROXIMAL_RECLAIM:
- touch_low >= demand_low
- touch_close > demand_high

B. CLEAN_IN_ZONE_HOLD:
- touch_low >= demand_low
- demand_low <= touch_close <= demand_high

C. SWEEP_FULL_RECLAIM:
- touch_low < demand_low
- touch_close > demand_high

D. SWEEP_PARTIAL_RECLAIM:
- touch_low < demand_low
- demand_low <= touch_close <= demand_high

## Adaptive entry state machine

### A — immediate clean reclaim
At the first retest close:
- entry timestamp = retest 15m close
- entry reference = retest close
- structural invalidation reference = H1 demand_low

Reason: the distal demand remained intact and the proximal boundary is already reclaimed.

### C — immediate sweep reclaim
At the first retest close:
- entry timestamp = retest 15m close
- entry reference = retest close
- structural invalidation reference = actual retest sweep low

Reason: demand_low was intentionally swept intrabar; the structurally relevant protected point becomes the sweep low after a complete reclaim above demand_high.

### B/D — pending reclaim
No entry at the first retest close.

Starting with the next completed 15m bar:
- maintain whether any low has swept below demand_low;
- maintain the lowest low observed from first touch through confirmation;
- if a 15m close < demand_low before proximal reclaim, cancel the setup;
- otherwise the first 15m close > demand_high confirms entry.

At confirmation:
- if no sweep occurred from touch through confirmation:
  - execution mode = DELAYED_CLEAN_RECLAIM
  - structural invalidation reference = demand_low
- if any sweep occurred:
  - execution mode = DELAYED_SWEEP_RECLAIM
  - structural invalidation reference = lowest low from touch through confirmation

This allows a first-touch B event to evolve into a sweep-reclaim execution if liquidity is taken before confirmation.

## Structural target ladder

Targets are not percentages and are not fitted reward multiples.

At the entry close, collect only levels already known at that time:

1. every confirmed 15m pivot high with:
   - pivot_ts >= H1 demand activation
   - confirm_ts <= entry_ts
   - level > entry
2. the frozen pre-retest expansion_high if > entry
3. every confirmed H1 pivot high with:
   - pivot_ts >= H1 demand activation
   - confirm_ts <= entry_ts
   - level > entry

Sort unique levels by price ascending.

- TP1 structural objective = nearest overhead known level
- TP2 structural objective = next known level, if any
- TP3 structural objective = third known level, if any

Persist the source of every objective.

No trade is rejected because of reward/risk in S3. Reward/risk is measured descriptively only.

## Structural risk geometry

Persist:
- entry - invalidation reference
- risk in H1 demand-zone widths
- risk as entry percentage
- room to TP1/TP2/TP3 in zone widths
- structural RR to each target
- delayed confirmation wait bars
- whether the first-touch archetype changed into a different execution mode during waiting

## No-target state

If no confirmed structural objective exists above entry at the entry close, mark `NO_KNOWN_OVERHEAD_OBJECTIVE`.

Do not invent a fixed target.

## Outputs

Persist:
- adaptive execution-plan ledger for all 788 parent events
- transition matrix from first-touch archetype to execution outcome/mode
- entry/cancel/no-trigger counts
- risk geometry by execution mode
- structural target availability/source counts
- support by year

## Stop rule

Do not:
- evaluate TP hit rates, stop hit rates, PnL, fees, leverage, expectancy, or WR
- optimize buffers around SL
- optimize entry offsets
- filter trades by RR
- add indicators, sessions, funding, volume, ATR, or derivatives
- alter the frozen B38 structural parent
- open 2025-2026 as validation in S3
