# BNB B38-S9 — Genuine Zone-Failure Structural Confirmation Audit

**Scientific identity:** `BNB_B38_S9_ZONE_FAILURE_CONFIRMATION_V1`

## Purpose

Identify whether genuine B38 demand-zone failures can be avoided **at the existing entry decision** using native causal structure, while measuring how many already-observed baseline WINs would be sacrificed.

This is not a threshold search and does not change TP/SL.

## Population

Exact frozen B38-S3 ENTRY plans with an available B38-S5 required target.

Periods:
- DEV: 2022-2024
- REF: 2025 through final available 2026 bar

## Baseline

Exact B38-S5 trade result:
- IMMEDIATE_CLEAN -> TP1
- IMMEDIATE_SWEEP -> TP1
- DELAYED_CLEAN -> TP1
- DELAYED_SWEEP -> TP2
- same S3 structural SL
- 5m target-vs-SL ordering.

Genuine zone failure uses the frozen S7 diagnostic:
- no completed 15m close above demand_high + 1 demand-width
- before first completed 15m close below demand_low.

## Native structural confirmations tested

Every condition is evaluated **at the existing S3 entry close only**.

### K1 BREAK_FIRST_TOUCH_HIGH
Entry close > frozen first-touch 15m high.

Interpretation: reclaim has progressed beyond the entire first interaction candle.

### K2 BULLISH_DISPLACEMENT_BREAK_PREV_HIGH
Entry candle is bullish AND entry close > previous completed 15m high.

Interpretation: entry close itself demonstrates immediate bullish displacement.

### K3 TWO_CLOSE_PROXIMAL_HOLD
Previous completed 15m close > demand_high AND entry close > demand_high.

Interpretation: proximal reclaim survived for two consecutive completed closes.

### K4 POST_TOUCH_CONFIRMED_MICRO_BOS
There exists a strict 2L/2R 15m pivot high with:
- pivot_ts >= first_touch_ts
- confirm_ts <= entry_ts
and entry close > that pivot-high level.

Interpretation: a post-touch local high was confirmed causally and then broken by entry.

### K5 BREAK_TOUCH_HIGH_AND_TWO_CLOSE_HOLD
K1 AND K3.

This is a preregistered structural conjunction, not outcome-derived.

## Evaluation

For each condition and period:
- accepted resolved trades;
- original S5 WR among accepted trades;
- total baseline WINs retained;
- total baseline WINs rejected;
- total baseline LOSSes rejected;
- genuine-zone-failure losses rejected;
- non-zone-failure losses rejected;
- loss rejected per baseline WIN sacrificed;
- trade-count retention.

Also report candidate outcome by execution mode.

## Preservation lens

No condition is called attractive unless its WIN retention is explicitly visible.
The audit does not automatically promote a condition even if WR rises.

## Stop rule

Do not:
- scan numeric thresholds;
- add time/session filters;
- combine conditions beyond K5;
- change entry price;
- change SL;
- change target;
- hide rejected baseline wins;
- relabel skipped losses as wins.
