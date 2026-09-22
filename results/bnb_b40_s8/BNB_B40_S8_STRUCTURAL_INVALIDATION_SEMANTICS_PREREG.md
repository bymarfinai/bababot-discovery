# BNB B40-S8 — Structural Invalidation Semantics Discovery Preregistration

## Objective
Distinguish healthy post-SD1 penetration/recycling from genuine structural failure.

S8 keeps the frozen B40 demand construction, SD1 detector, and MARKET_SD1_CLOSE entry unchanged.
It changes only the hard invalidation definition.

The key question is not only WHERE price trades, but WHETHER a structural level is merely wicked through or is actually accepted below on a completed close.

## Frozen parent
Use the persisted B40-S7 MARKET_SD1_CLOSE cohort only.

Frozen detector:
- SD1_CLOSE15_ABOVE_ANCHOR
- signature: c742621214a18aa46140bc10a37fcf9c482ea8e0c6d5bc11f8af634cec12f1d0

Frozen entry:
- MARKET_SD1_CLOSE

Expected parent parity:
- DEV: 286
- REF: 160

Expected raw-touch protected-low baseline from B40-S7:
- DEV: 149 WIN / 115 LOSS / 22 UNRESOLVED
- REF: 87 WIN / 59 LOSS / 14 UNRESOLVED

## Frozen audit target and horizon
- audit target = first-retouch anchor + 1.00 event-R
- deadline = 24h from first retest
- event-R definition unchanged from B40.

The +1 event-R objective remains audit geometry, not the final TP policy.

## Structural levels
Exactly two levels, both fully known at SD1 confirmation:

1. PROTECTED_LOW
   - B40 H1 source/base protected low.
   - This is the actual structural-consumption level used by B40 survival labeling.

2. REACTION_LOW
   - minimum low of the three raw 5m bars forming the frozen SD1 +15m reaction window.
   - This is the nearest completed post-touch reaction structure known at entry.

No ATR buffers, percentages, quartile offsets, or optimized levels are searched.

## Invalidation semantics
Each structural level is tested with exactly three semantics:

1. TOUCH
   - invalidate when any raw 5m low trades at/below the level.
   - if target and stop touch occur in the same raw 5m bar: AMBIGUOUS.

2. CLOSE5
   - invalidate only when a completed raw 5m close is below the level.
   - target is a resting objective; if target trades during a bar before that bar closes below the level, target wins first.
   - exit price on invalidation = the completed 5m close, not the structural level.

3. CLOSE15
   - invalidate only when the completed close of the next aligned 15m reaction window is below the level.
   - implemented as each third completed raw 5m close after SD1 decision, preserving the same post-touch 5m alignment used to construct SD1.
   - target remains live intrabar; if target trades before the 15m close-trigger, target wins.
   - exit price on invalidation = the completed 15m close.

Exactly six candidates:
- PROTECTED_LOW_TOUCH
- PROTECTED_LOW_CLOSE5
- PROTECTED_LOW_CLOSE15
- REACTION_LOW_TOUCH
- REACTION_LOW_CLOSE5
- REACTION_LOW_CLOSE15

## Risk normalization
Initial trade-risk denominator for every candidate:
`entry - structural_level`

WIN R:
`(target - entry) / initial_risk`

TOUCH loss:
- exactly -1R.

CLOSE5 / CLOSE15 loss:
`(exit_close - entry) / initial_risk`

Therefore close-trigger losses may be worse than -1R if the completed close overshoots the structural level. This is intentional and avoids fake economics.

## Required metrics
For DEV, REF, and each year:
- availability
- median structural-level distance from entry in event-R
- median risk compression vs PROTECTED_LOW_TOUCH
- wins / losses / ambiguous / unresolved
- resolved WR
- median/mean WIN R
- median/mean LOSS R
- loss-R 10th percentile (tail loss)
- expectancy per signal
- total R
- profit factor
- max drawdown
- max loss streak

### Structural failure / false-stop audit
For each candidate:
- frozen GE1R expanders available
- GE1R retained as WIN
- GE1R stopped before later target = false stop
- false-stop rate
- median stop -> later target time
- median maximum overshoot below invalidation level before later target

Also report:
- true B40 SURVIVE zones stopped
- true B40 CONSUMED zones stopped
- fraction of CONSUMED zones caught before target
- LOCAL_ONLY survivors stopped

## Decision boundary
A structural invalidation semantics is useful only if:
- it improves or preserves economics in both DEV and REF;
- it materially reduces false stops versus raw-touch semantics;
- loss overshoot from close confirmation does not create unacceptable tail losses;
- yearly behavior is not isolated to one year.

S8 must NOT choose the highest expectancy candidate if that result comes from unstable close overshoot or a tiny retained sample.

If CLOSE semantics clearly dominate TOUCH at the same level, B40 should treat penetration as liquidity/recycling and acceptance below structure as the real failure state.

If neither PROTECTED_LOW nor REACTION_LOW produces robust economics, S9 must study dynamic post-entry failure states rather than tune more static levels.
