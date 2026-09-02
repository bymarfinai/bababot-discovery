# ETH London -> New York M5 F90 Entry Trigger Calibration — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Calibrate the execution trigger at the structurally stable ETH F90 retracement anchor identified in M4, without changing the London->New York detector or using economics.

The only question is:

> After a valid K1 OPP0 -> causal leave -> pre-H2 F90 touch, does requiring a causal reclaim/rejection improve the probability of a later strict 5m breakout close above frozen London High compared with the original blind F90 limit fill?

M5 tests entry timing only. No stop, TP, PF, PnL, fee, slippage, runner, leverage, portfolio lock, alternate clock, indicator, candle-body threshold, wick threshold, or intermediate F-level sweep is allowed.

## Frozen cohort
- ETHUSDT perpetual, raw 5m.
- London reference: 08:00-13:30 UTC.
- New York active session: 13:30-20:00 UTC.
- LONG K1 OPP0 only.
- Reuse exact persisted M2 **F90 filled opportunities** and exact F90 touch bars.
- Historical partitions unchanged: external, development, reference_validation, August telemetry.
- `H`, `L`, and `R=H-L` remain frozen from London.
- `F90 = L + 0.90R`.

## Frozen variants

### 1. BLIND_TOUCH — control
Use the exact M2 F90 limit fill:
- entry bar = persisted M2 `entry_ts`;
- entry price = exact F90;
- no confirmation requirement.

This control must reproduce M4 F90 strict-breakout counts/rates exactly.

### 2. EARLY_RECLAIM — only selectable candidate
Starting with the exact F90 touch/fill bar:
1. If that completed bar closes strictly above F90, it is the reclaim confirmation.
2. Otherwise inspect later completed raw 5m bars strictly before H2 arrival.
3. The first completed bar with `close > F90` confirms.
4. If H2 arrives before confirmation, the setup expires.
5. If any completed bar closes `< L` before confirmation, the setup expires.
6. If New York ends before confirmation, the setup expires.
7. No `close > previous-high`, EMA, ATR, volume, body, wick, RSI, or other condition is allowed.

Execution is the OPEN of the immediately following raw 5m bar.
- If that next open is `>= H`, reject as `MISSED_H2_AT_OPEN`.
- If that next open is `<= L`, reject as `INVALID_OPEN_GEOMETRY`.
- If `L < open < H`, execution is valid even if that same bar later becomes H2 or strict breakout; the open is chronologically earlier than its intrabar high/close.

### 3. SAME_BAR_REJECTION — diagnostic subset only
A strict subset of EARLY_RECLAIM:
- the original F90 touch bar itself closes strictly above F90;
- entry is the next raw 5m open under the same geometry rules.

This subset cannot be promoted independently and cannot justify new candle-shape thresholds.

## Frozen structural outcome
From each actual execution bar through 20:00 UTC:
- `STRICT_BREAKOUT`: first completed raw 5m `close > H`, provided no earlier completed raw 5m `close < L`.
- `OPPOSITE_BREAK`: first completed raw 5m `close < L` before strict breakout.
- `NO_BREAK_BY_END`: neither occurs by session end.

H2 remains telemetry only; wick-only arrival to H is not success.

## Required reporting
For each partition and variant:
- F90 touch opportunities;
- confirmed count;
- executed count and execution/retention rate;
- same-bar vs later reclaim count;
- strict-breakout count/rate among executed entries;
- opposite-break count/rate;
- no-break count/rate;
- H2-after-entry rate;
- median minutes F90 touch -> confirmation;
- median minutes F90 touch -> actual entry;
- median realized entry fraction `(entry_px-L)/R`;
- median remaining distance to H in R units.

Persist one row per F90 opportunity/variant with touch, confirmation, entry, H2, terminal event, and realized entry fraction.

## Frozen trigger screen
Only **EARLY_RECLAIM** may receive `TRIGGER_SCREEN_PASS`, and only if all conditions hold:
1. At least **15 executed entries in each** external, development, and reference_validation.
2. Pooled-major execution retention is at least **60%** of BLIND_TOUCH.
3. Strict-breakout rate is **not lower than BLIND_TOUCH in any** of the three major partitions.
4. Pooled-major strict-breakout rate improves by at least **3.0 percentage points** versus BLIND_TOUCH.

SAME_BAR_REJECTION is diagnostic regardless of its observed rate.

If EARLY_RECLAIM fails, M5 does not authorize F89/F91, confirmation-window thresholds, body/wick filters, indicators, or post-hoc trigger mining.

## Mandatory assertions
1. Exact M2 F90 filled-opportunity identity and touch timestamps are reused unchanged.
2. BLIND_TOUCH strict-breakout counts/rates reproduce M4 F90 exactly for each major partition and pooled-major.
3. Reclaim confirmation requires completed `close > F90`.
4. No reclaim confirmation completes on/after the H2 bar.
5. No confirmation occurs after completed `close < L`.
6. Reclaim entry is exactly the next raw 5m open after confirmation.
7. Next-bar entry on an H2 bar is allowed only if its open is `< H` and `> L`.
8. No executed reclaim entry is at/above H or at/below L.
9. Strict breakout requires completed `close > H`; wick-only H2 never counts.
10. No event after 20:00 UTC is scored.
11. Raw ETH 5m coverage must be >=99.5%.
12. Synthetic tests must cover same-bar reclaim, later reclaim, H2-before-confirmation expiry, opposite-break-before-confirmation expiry, entry-on-H2-bar-open, missed-H2-at-open, and no-break-by-end.

Research only. Live BBC unchanged.