# SOL SELL Structural Character V2 — Adaptive Grammar Preregistration

## Purpose

The goal is **not** to reproduce one chart candle-for-candle.

The goal is to detect the same structural grammar across different SOL price geometries:

**buy-side liquidity raid -> bearish structural shift / new low -> corrective return into bearish origin area -> structural downside continuation**

Entry timing, TP and SL are deliberately excluded. They will be discovered later only if this structural character proves real.

## Core invariants

A valid family member must preserve the following order:

1. **Liquidity is taken above an already-confirmed H1 swing high.**
2. **Price subsequently reclaims below that high and breaks a significant confirmed H1 low.**
3. **A bearish origin / break-block area exists inside the raid-to-BOS leg.**
4. **Price later corrects back into that origin area.**
5. **After the return, price either makes a fresh structural low before invalidating the origin, or invalidates the origin first.**

Candle shapes, exact sweep depth, exact displacement size, return delay, and micro-entry candle do **not** need to match the reference chart exactly.

## Frozen data

- Symbol: SOLUSDT.
- Structural timeframe: H1 built from complete 5m bars.
- Child path timeframe: 5m.
- Development window: 2020-2024.
- 2025+ CLOSED.
- Minimum 5m coverage: 99.5%.
- No hour/session filter.
- No EMA, RSI, Fibonacci, volume, regime, TP, SL or fixed profit target.
- No post-result threshold rescue.

## Causal pivots

Use the frozen causal order-2 H1 pivot semantics from the SOL structure library.

A pivot is usable only after its confirmation bar.

## Stage A — liquidity raid family

For the latest unconsumed confirmed H1 swing high H0:

- a completed H1 bar trades above H0;
- reclaim may occur on the same H1 bar or within the next **2 completed H1 bars**;
- reclaim means a completed H1 close < H0;
- the significant-low reference L0 is the latest confirmed H1 swing low whose pivot is after H0 and whose confirmation was already known before the raid;
- H0 is consumed by the first completed raid/reclaim family event.

This deliberately allows different candle shapes while preserving the liquidity principle.

## Stage B — bearish structural shift

After reclaim:

- inspect at most **16 completed H1 bars**;
- the first completed H1 close < L0 is the bearish BOS;
- before BOS, no completed H1 close may exceed the raid extreme;
- no hard displacement threshold is used;
- instead record displacement size, path efficiency, BOS extension and timing as character features.

The bearish origin / break block is the **last bullish H1 candle from raid through the bar before BOS**.

Frozen zone geometry for V2 is the full H1 origin-candle range. This intentionally uses a broad structural area rather than an exact price line.

## Stage C — corrective return

Starting after the BOS H1 candle closes:

- search up to **14 calendar days** of completed 5m bars;
- the first 5m bar whose range overlaps the origin zone is the structural return;
- no rejection candle is required at this phase.

The lowest 5m low reached from BOS close until immediately before the return becomes the **pre-return structural low**.

## Stage D — structural response label

Starting from the first return, inspect the next **24 hours** of completed 5m bars.

Two competing structural outcomes:

### CONTINUATION
Price trades below the pre-return structural low before origin invalidation.

### INVALIDATED
A completed 5m candle closes above the origin-zone high before a fresh structural low.

If both are unknowable on the same 5m bar, label AMBIGUOUS.
If neither occurs within 24h, label UNRESOLVED.

This is a structural label, **not** a trading exit rule.

## Required outputs

Persist:

- Stage A raid/reclaim events;
- Stage B BOS + origin events;
- Stage C return events;
- Stage D response labels;
- overall and yearly continuation-vs-invalidation rates;
- timing distributions;
- structural feature inventory:
  - raid depth;
  - reclaim delay;
  - sweep-to-BOS bars;
  - displacement in recent-range units;
  - bearish path efficiency;
  - BOS extension;
  - BOS-to-return delay;
  - zone width;
  - return penetration.

## Interpretation

The primary question is:

> When SOL performs this **topological sequence**, does a return into the bearish origin area tend to resolve by making another structural low before the origin is invalidated?

Do not judge this phase by a fixed +60m PnL or by a fixed TP/SL.

If the character is supported, the next lineage is:

**adaptive entry discovery -> adaptive invalidation/SL discovery -> adaptive objective/TP discovery**

2025_PLUS=CLOSED
