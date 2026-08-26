# ETH LONG B27AA-Adapt — Early F75 Rejection / Reclaim Filter — Preregistration

## Purpose
Adapt the BTC B27AA milestone to ETH without changing the frozen structural detector or F75 location.

Hypothesis: blind F75 touches mix healthy pullbacks with continuation-down paths; the earliest causal reclaim of F75 may improve economics.

## Frozen source cohort
- ETHUSDT
- LONDON_TO_NEWYORK LONG
- K1 OPP0
- causal leave after first High-touch episode
- exact B27W-Adapt F75 touch/fill identities
- same partitions

No F-level resweep is allowed.

## Frozen levels and economics
Use the ranking leader from completed B27Z-Adapt, without changing it:
- touch/reclaim level: F75
- close-invalidation: D60 = F15
- target: E10
- notional USD 500
- round-trip fee USD 0.40

H2 remains a milestone, not TP.

## Primary confirmation — EARLY_RECLAIM
Starting on the exact F75 touch bar:
1. Touch bar confirms if its completed close is strictly above F75.
2. Otherwise use the first later completed 5m bar whose close is strictly above F75.
3. If H2 occurs before confirmation completes, expire.
4. If completed close < L before confirmation, expire.
5. If session ends before confirmation, expire.
6. No candle-shape, EMA, ATR, volume, regime, or other indicator condition.

Entry is the next raw 5m open after confirmation. If that open is >= H, reject as MISSED_H2_AT_OPEN. Entry must satisfy F15 < entry < H.

## Secondary diagnostic — SAME_BAR_REJECTION
Strict subset where the original F75 touch bar itself closes > F75. Entry is the next 5m open under the same chronology and economics.

Diagnostic only; it cannot rescue a failed EARLY_RECLAIM gate.

## Exit chronology
- Resting TP E10 is evaluated intrabar from the entry bar onward.
- Completed-close invalidation below F15 exits at actual close.
- On a later bar where TP and close invalidation both occur, TP takes precedence because close invalidation is only observable at completion.
- H2 alone never exits.
- Otherwise exit at session-end open.

## Frozen screen
EARLY_RECLAIM passes only if in each external, development, reference_validation:
- >=30 executed trades
- WR >=70%
- PF >=1.20
- positive expectancy

Research only; no live changes.