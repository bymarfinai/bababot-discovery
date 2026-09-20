# BNB B37-S4 — Causal Structural Detector State Machine Preregistration

**Scientific identity:** `BNB_B37_S4_CAUSAL_STATE_MACHINE_V1`

## Purpose

Step 4 turns the four frozen Step-3 structural hypotheses into an explicit causal state machine suitable for live-bar execution.

This step does **not** evaluate winner/loss outcomes, win rate, TP/SL, PnL, economics, sessions, indicators, derivatives, or 2025-2026 reference data.

## Required equivalence

The state-machine replay on 2022-2024 must reproduce the frozen Step-3 event membership exactly:

- B37-S1B visual-equivalent parent events: **201**
- C1 `H4D_H1_PROXIMAL_RECLAIM`: **133**
- C2 `H4D_H1_CLEAN_PROXIMAL_RECLAIM`: **115**
- C3 `H4D_H1_BULLISH_PROXIMAL_RECLAIM`: **27**
- C4 `H4D_H1_CONTROLLED_EXPANSION_CLEAN_RECLAIM`: **40**

Event identity is `(zone_id, first_touch_ts)`.

Any mismatch is a Step-4 failure. No rule may be changed to rescue equivalence without a new scientific identity.

## Multi-zone architecture

Each H4 demand zone is an independent detector instance. Multiple zones may coexist.

### H4 state creation

`WAIT_H4_STRUCTURE -> DEMAND_REGISTERED`

A demand instance is created only when the frozen B37-S1 causal H4 structure occurs:

1. strict H4 swing high with 2 bars left and 2 bars right;
2. swing becomes usable only after the second right-side H4 bar closes;
3. prior H4 close <= confirmed swing-high price;
4. current H4 close > confirmed swing-high price;
5. origin = latest bearish H4 candle among the prior six completed H4 bars;
6. demand_low = origin low;
7. demand_high = origin open;
8. one demand zone per broken H4 swing high.

## Per-zone H1 lifecycle

### State A — `WAIT_EXPANSION`

After H4 activation, wait for a strict H1 pivot high:
- pivot has 2 left + 2 right bars;
- usable only at the second-right-bar close;
- pivot timestamp > H4 activation;
- pivot high > max(H4 broken swing level, H4 BOS close).

When confirmed:
`WAIT_EXPANSION -> EXPANSION_CONFIRMED`

### State B — `EXPANSION_CONFIRMED`

Store the latest eligible confirmed H1 expansion pivot:
- pivot timestamp
- confirmation timestamp
- expansion high

If another eligible H1 expansion pivot is confirmed before first retest, replace the stored expansion with the newer pivot. This reproduces the frozen B37-S1B use of the latest confirmed expansion high before retest.

### State C — `WAIT_FIRST_RETEST`

For every H1 bar strictly after H4 activation, the **first** bar whose range overlaps the H4 demand zone ends the waiting phase.

Important causal ordering at H1 close `t`:
1. first-retouch evaluation occurs using expansion pivots confirmed strictly before `t`;
2. only if the bar is not the first touch may a pivot newly confirmed at `t` update the zone for future bars.

Thus a pivot confirmed on the retest bar itself cannot be used.

### State D — `RETEST_EVALUATED`

At first retest, calculate the frozen visual-equivalent parent:

- stored eligible expansion exists;
- retest close >= demand_low;
- >=2 completed H1 bars exist after expansion pivot and before retest;
- that path contains at least one lower-high observation OR one lower-low observation.

If false:
`RETEST_EVALUATED -> TERMINAL_REJECT`

If true:
`RETEST_EVALUATED -> PARENT_DETECTED`

### State E — candidate detector fire

For a `PARENT_DETECTED` event, evaluate the four frozen candidate rules at the retest H1 close:

- C1 `PROXIMAL_RECLAIM`: touch_close > demand_high
- C2 `CLEAN_PROXIMAL_RECLAIM`: C1 AND touch_low >= demand_low
- C3 `BULLISH_PROXIMAL_RECLAIM`: C1 AND touch_close > touch_open
- C4 `CONTROLLED_EXPANSION_CLEAN_RECLAIM`: C2 AND (expansion_high - h4_bos_close <= demand_width)

The detector emission timestamp is the first-retest H1 close.

After first retest, the zone is terminal and cannot emit again.

## Causality constraints

- H1 and H4 are reconstructed from exact closed 5m bars.
- No bar after detector fire may contribute to membership.
- No forward outcome labels may be loaded in Step 4.
- 2025-2026 remains unopened.
- Multiple H4 demand instances are processed independently.

## Outputs

Persist:
- state-machine parent event ledger;
- terminal reject reason census;
- detector emission ledger;
- support by year;
- exact equivalence comparison vs frozen Step 3;
- transition census;
- Step-4 result.

## Gate

`STATE_MACHINE_EQUIVALENCE_PASS` requires:
- 201/201 parent event identity match;
- zero extra parent events;
- zero missing parent events;
- zero C1/C2/C3/C4 flag mismatches;
- candidate totals 133/115/27/40.

Only after this gate may Step 5 validation begin.
