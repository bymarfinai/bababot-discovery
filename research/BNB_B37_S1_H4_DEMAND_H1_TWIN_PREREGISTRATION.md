# BNB B37-S1 — H4 Demand / H1 Pullback Structural Twin Preregistration

**Scientific identity:** `BNB_B37_S1_H4_DEMAND_H1_TWIN_V1`

## Purpose

Step 1 only: find BNB historical structures that are structurally identical to the supplied educational setup.

This phase is **structure-only**. It does not calculate win rate, TP/SL, PnL, forward returns, session effects, indicators, derivatives, or any economic outcome.

## Supplied structure translated into causal states

The visual setup is treated as a multi-timeframe sequence:

1. **H4 bullish demand is created by structure**, not by an arbitrary horizontal support.
2. The H4 move closes above a previously confirmed H4 swing high (bullish BOS / impulse).
3. The demand origin is the **latest bearish H4 candle before that BOS**. Zone = candle low to candle open.
4. After the H4 BOS, that demand must remain **fresh** until the target retest.
5. On H1, price must produce a causal bullish BOS above a previously confirmed H1 swing high.
6. H1 must subsequently print a **new local high**, confirmed causally by two closed H1 bars on the right.
7. Price then enters a corrective retracement: after the new-high pivot, at least one lower high and one lower low must print before the retest.
8. The **first H1 touch** of the H4 demand after activation is the target retest. It must not close below the H4 demand low.

An event is an **EXACT STRUCTURAL TWIN** only when every state above is true in sequence.

## Causality

- Source: immutable Binance USD-M BNBUSDT 5m history already used by B31/B35.
- H1 bars: exactly 12 consecutive closed 5m bars.
- H4 bars: exactly 48 consecutive closed 5m bars.
- Swing definition on both H1 and H4: strict 2-left / 2-right pivot.
- A swing is usable only after the second right-hand bar has closed.
- No future information after the retest candle is used to decide whether a twin exists.

## Discovery universe

- Structural-twin discovery is restricted to **2022-01-01 through 2024-12-31**.
- 2025-2026 remains unused in this step.
- No forward outcome after the retest is opened.

## H4 demand state

At H4 bar `t`:
- latest confirmed H4 swing high must already be known before `t`;
- previous H4 close <= swing-high level;
- current H4 close > swing-high level;
- latest bearish H4 candle among the six completed H4 bars immediately before BOS is the demand origin;
- demand low = origin low;
- demand high = origin open;
- one demand zone per broken H4 swing high.

The six-bar origin search is a **zone-construction convention**, not an outcome-tuned filter.

## H1 impulse / new-high state

Before the first H1 demand touch:
- at least one H1 bullish BOS must occur after the H4 demand activation;
- that H1 BOS must break a swing high confirmed before the BOS bar;
- a later H1 pivot high above the broken H1 level must be confirmed before the demand retest.

## Retracement state

Between the new-high pivot and the first H1 demand touch:
- at least two completed H1 bars must exist;
- at least one sequential lower-high observation and one sequential lower-low observation must occur.

No percentage retracement threshold is allowed.

## Fresh retest

The target is the first H1 candle after H4 demand activation whose range overlaps the H4 demand zone.

Exact twin requires:
- the new-high and retracement states already exist before the touch;
- retest close >= demand low;
- there was no earlier H1 overlap with the zone after activation.

## Output

Persist:
- exact-twin ledger;
- state/checklist ledger;
- structure-only summary;
- up to six H1 chart snapshots with the H4 demand zone drawn.

## Stop rule

Do not add indicators, clock filters, ATR thresholds, derivatives, outcome labels, or rescue rules in B37-S1.

If zero exact twins exist, report zero. Any revised structural interpretation must receive a new identity before rerun.
