# BNB B38-S2 — H1 Demand / 15m Structural Archetype Discovery

**Scientific identity:** `BNB_B38_S2_H1D_15M_ARCHETYPES_V1`

## Purpose

B38-S2 studies the frozen B38-S1 **H1-demand / 15m-execution** visual family only.

Goal: identify a small set of **causal demand-interaction archetypes** that can later support different adaptive entry, structural invalidation, and target logic.

This is not TP/SL optimization and is not an out-of-sample claim.

## Population

- BNBUSDT
- exact H1 demand
- exact 15m execution
- B38-S1 visual-equivalent family
- 2022-01-01 through 2024-12-31
- expected parent N = **788**

## Primary archetypes

Archetypes use only the first 15m retest candle and the already-known H1 demand boundaries. They are mutually exclusive and exhaustive within the parent family.

### A — CLEAN_PROXIMAL_RECLAIM
- touch_low >= demand_low
- touch_close > demand_high

Meaning: demand distal remains intact and the first 15m interaction closes back above the proximal edge.

### B — CLEAN_IN_ZONE_HOLD
- touch_low >= demand_low
- demand_low <= touch_close <= demand_high

Meaning: demand distal remains intact, but the first 15m close is still inside the zone.

### C — SWEEP_FULL_RECLAIM
- touch_low < demand_low
- touch_close > demand_high

Meaning: price sweeps the distal edge intrabar and recovers the entire H1 demand zone by 15m close.

### D — SWEEP_PARTIAL_RECLAIM
- touch_low < demand_low
- demand_low <= touch_close <= demand_high

Meaning: price sweeps the distal edge and only reclaims back inside the zone by 15m close.

No learned threshold is used. Only native demand_low/demand_high boundaries define the archetypes.

## Pre-entry structural geometry

At the retest close persist:

- demand width
- zone penetration fraction
- close position in zone-width units
- touch candle close location
- bullish/bearish touch polarity
- pullback bars from expansion pivot
- expansion distance above H1 BOS in zone-width units
- expansion distance above demand in zone-width units
- risk from touch close to demand_low in zone-width units
- risk from touch close to touch_low in zone-width units
- nearest already-confirmed 15m overhead pivot high before retest
- room from touch close to nearest overhead pivot high in zone-width units
- room from touch close to expansion high in zone-width units
- 3-vs-3 pre-touch range compression ratio where available

## Descriptive forward path

Using bars strictly after the retest and before the first 15m close below demand_low / end-2024, persist:

- +1 zone-width rebound
- +2 zone-width rebound
- full continuation above expansion_high
- maximum favorable close excursion in zone widths
- bars to +1ZW
- adverse excursion before +1ZW for successful +1ZW events
- bars to structural invalidation for failures

These are descriptive path statistics, not entry/TP/SL rules.

## Stability view

For each archetype report:
- N by year
- +1ZW rebound rate pooled and separately 2022/2023/2024
- +2ZW rate
- full-continuation rate
- MFE distribution
- structural risk/room medians
- touch polarity and compression composition

No archetype is declared “best” in S2.

## Adaptive-execution mapping

S2 may state only the **execution question** implied by each archetype:

- CLEAN_PROXIMAL_RECLAIM: can immediate reclaim entry work with distal-zone invalidation?
- CLEAN_IN_ZONE_HOLD: is a later 15m confirmation needed before entry?
- SWEEP_FULL_RECLAIM: should the sweep low replace demand_low as structural invalidation?
- SWEEP_PARTIAL_RECLAIM: does this require a later micro-BOS/reclaim before entry?

Actual rules are frozen only in B38-S3 after S2 evidence is reviewed.

## Stop rule

Do not:
- optimize entry price
- optimize TP
- optimize SL
- select thresholds by performance
- add indicators, sessions, derivatives, ATR, funding, or volume filters
- open 2025-2026 for validation
