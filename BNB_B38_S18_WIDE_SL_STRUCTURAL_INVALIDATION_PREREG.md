# BNB B38-S18 — Wide-SL Structural Invalidation Audit Preregistration

## Objective
For the frozen E2 trades whose baseline structural stop is unusually wide, identify whether a closer invalidation level exists that remains causal and structurally defensible.

## Frozen upstream
- E2 signature: `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
- Baseline SL: first-touch-to-entry low
- Baseline TP: causal TP1
- Wide-SL definition frozen from S17 DEV Q75:
  `baseline_sl_pct > 0.017122292197580727`

Expected wide-SL population:
- DEV: 110
- REF: 50

## Causal structural candidates
All candidate levels must already exist at E2 entry time.

1. **TOUCH_LOW_BASELINE**
   - Existing first-touch-to-entry low.

2. **RECLAIM_LOW**
   - Lowest 15m low from reclaim bar through entry.
   - Already part of the S11 frozen geometry family.

3. **HOLD_LOW**
   - Low of the E2 hold bar: the first completed 15m bar after reclaim whose close remains at/above demand_high.
   - This directly invalidates the "reclaim -> hold" leg if broken.

4. **PROTECTED_PIVOT_LOW**
   - Latest confirmed 15m pivot low after reclaim with confirmation timestamp no later than entry.
   - Pure confirmed local structure; unavailable trades remain explicitly unavailable.

5. **DEMAND_LOW_TOUCH**
   - Original H1 demand low as a touch stop.

6. **DEMAND_LOW_CLOSE15**
   - Original H1 demand low as 15m close invalidation.
   - Included because the E2 state machine itself uses close below demand_low as structural acceptance failure before entry.

## Audit outputs
For DEV and REF separately:
- candidate availability
- median stop distance %
- median stop compression vs baseline
- baseline WIN survival to TP1
- baseline WIN false-stop count/rate
- baseline LOSS converted to WIN
- WR / expectancy / total R under frozen TP1
- annual stability

For baseline WINs that false-stop under a closer candidate:
- whether price later reaches TP1 after the candidate invalidation
- median time from false-stop to eventual TP1
- median adverse excursion below candidate before eventual TP1

## Decision boundary
S18 is diagnostic only.
No closer stop is promoted unless it:
- materially compresses stop distance,
- preserves baseline winners at a high rate in both DEV and REF,
- does not rely on future structure,
- and shows economically coherent behavior across years.
