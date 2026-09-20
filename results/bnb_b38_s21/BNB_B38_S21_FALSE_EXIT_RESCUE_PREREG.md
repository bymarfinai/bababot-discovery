# BNB B38-S21 — Rescue False-Exit Winner Preregistration

## Objective
Among Q4-wide E2 trades that already trigger the S20 failure state
`5m close < reclaim_close`, determine whether a causal recovery structure can
rescue eventual TP1 winners without allowing most true losers to continue to the
original -1R structural stop.

## Frozen upstream
- E2 signature:
  `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
- Q4-wide cut:
  `baseline_sl_pct > 0.017122292197580727`
- S20 failure trigger:
  first clean 5m close below frozen reclaim close, before TP1 and structural SL.

Expected clean-trigger population:
- DEV: 31 = 21 baseline LOSS + 10 baseline WIN
- REF: 8 = 6 baseline LOSS + 2 baseline WIN

## Principle
S21 does not alter detector, entry, TP1, or original structural SL.
The S20 trigger remains the starting failure event.

Recovery observations begin strictly after the S20 failure-signal bar.

## Preregistered recovery characters

1. **NEXT5_RECLAIM**
   - next completed 5m close is back at/above reclaim_close.

2. **NEXT15_RECLAIM**
   - first completed 15m close after the failure event is at/above reclaim_close.
   - if original TP1 or structural SL resolves before that 15m close, the state is unresolved for rescue.

3. **RECLAIM_HOLD**
   - a completed 5m close reclaims reclaim_close,
   - followed by the next completed 5m close remaining at/above reclaim_close,
   - before original structural SL.

4. **RECLAIM_FAILURE_HIGH_BREAK**
   - after a completed 5m reclaim of reclaim_close,
   - a later completed 5m close breaks above the high of the original failure-signal 5m bar,
   - before structural SL.

5. **RECLAIM_BREAK_LEVEL**
   - after the failure event, a completed 5m close returns above the frozen E2 breakout threshold,
   - before structural SL.

No numeric depth threshold, percentile cut, or optimized bar-count window is introduced.

## Discovery outputs
For DEV and REF separately:
- recovery coverage among false-exit baseline WINs
- recovery leakage among true baseline LOSSes
- recovery precision = eventual baseline WIN / all recovery signals
- time from failure trigger to recovery
- adverse excursion after failure trigger before recovery
- remaining time to baseline TP1 for rescued winners
- remaining time to structural SL for leaked losers

## Counterfactual rescue policies
For each recovery character:
- at S20 failure trigger, do NOT exit immediately;
- observe only the preregistered recovery state;
- if recovery occurs before structural SL, restore the original frozen baseline path;
- if the recovery state fails according to its own natural confirmation event, exit at that event close;
- ambiguous same-bar states are not silently resolved.

The main purpose of S21 is separator discovery, not promotion.

## Stop rule
This is the only false-exit rescue discovery round.
If no recovery character separates baseline WIN vs LOSS consistently in DEV and REF,
do not add more rescue filters before moving to expansion-character discovery.
