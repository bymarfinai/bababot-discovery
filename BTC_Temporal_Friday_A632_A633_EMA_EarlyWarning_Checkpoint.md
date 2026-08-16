# BTC Temporal Friday15 — A6.32–A6.33 EMA Early-Warning Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** PROVISIONAL EMA DAMAGE-CONTROL UPGRADE — NOT LIVE / NOT FRESH OOS PROVEN  
**Symbol:** BTCUSDT  
**Entry:** every Friday exact 15:00 WIB BUY  
**Sample:** 138 Fridays; first82 discovery / last56 validation  
**Live BBC:** untouched

## Reference before EMA study — A6.30

- N138
- WR 60.87%
- PnL +$137.132
- expectancy +$0.9937/Friday
- PF 1.686
- max DD $49.350
- LS4
- validation -$1.448
- rule: frozen 60m FULL failure warning -> tighten first-leg BUY stop from -0.70% to -0.50% until120m; downstream A6.22 management unchanged.

## A6.32 — EMA structure study

Tested strict-causal EMA structures at 30/45/60m using completed 5m data only. Action remained conditional stop cap -0.50%; no entry filtering and no TP/SL retuning.

Main findings:

1. **30m is too early.** Bearish stack/rejection can identify many eventual losses but still damages delayed winners; discovery economics are negative for the broad 30m stack family.
2. **45m is materially better.** The structural state
   - actual checkpoint open < completed EMA7 < completed EMA20,
   - EMA7 falling over the prior 15m,
   - EMA20 falling over the prior 15m,
   - EMA7-EMA20 spread widening bearish,
   produced:
   - discovery: 5 actions, 5 original losers, 100% loss precision, +$2.418 delta vs A6.22 baseline;
   - validation: 8 actions, 7 losers / 1 winner, +$6.969 delta;
   - full: 13 actions, 12 losers / 1 winner, 92.31% loss precision, +$9.387 delta;
   - WR unchanged at 60.87%; no baseline-positive occurrence became negative.
3. **60m EMA stack also works**, but later:
   - discovery 3/3 actions were original losers, +$2.526 delta;
   - validation 5/6 original losers, +$4.056 delta;
   - full PnL +$135.570 vs A6.22 +$128.989.
4. Single-candle EMA7/EMA20 rejection is too sparse/noisy to replace the structural stack.

Interpretation: EMA is useful as a **state sensor for persistent bearish acceptance**, not as a standalone entry edge. The meaningful pattern is not a simple cross; it is price below both EMAs, fast EMA below slow EMA, both slopes down, and bearish spread expansion.

## A6.33 — EMA45 early warning + frozen FULL60 fallback

Predeclared sequential management architecture:

1. Every Friday15 BUY still enters; parent TP2.0 / SL0.7 / max6h.
2. At45m, using completed 5m data only, check bearish EMA stack+widen:
   - price < EMA7 < EMA20;
   - EMA7 down over prior15m;
   - EMA20 down over prior15m;
   - EMA7-EMA20 spread widening bearish.
3. If true, arm first-leg protective stop at **-0.50%** immediately from45m until120m.
4. If no EMA45 warning, retain the already-frozen A6.30 FULL warning at60m as fallback and arm the same -0.50% cap.
5. At120m and beyond, A6.22 downstream logic remains unchanged:
   - confirmed post-stop failure can open sequential SHORT TP1.5 / SL0.5;
   - existing still-open failed-thesis handling remains;
   - existing distribution/giveback logic remains.

### A6.33 results

Full:
- N **138/138**
- WR **60.87% unchanged**
- PnL **+$141.025**
- expectancy **+$1.0219/Friday**
- PF **1.720**
- max DD **$46.318**
- LS **4**
- delta vs A6.22 baseline +$12.036
- delta vs A6.30 reference +$3.893

Discovery first82:
- WR67.07%
- +$139.472
- PF2.549
- delta vs A6.22 +$2.418
- 5 realized damage-control actions, all 5 original losers.

Validation last56:
- WR51.79%
- **+$1.553**
- PF1.015
- delta vs A6.22 +$9.618
- improvement vs A6.30 validation -$1.448 = +$3.001
- 13 realized actions across EMA45/fallback route; 11 original losers / 2 original winners.

Full attribution:
- 18 realized damage-control actions
- 16 original losers / 2 original winners
- loss precision **88.89%**
- 14 losses became less negative vs A6.22
- **0 baseline-positive occurrences became negative**
- loss-side delta +$11.623
- winner-side delta +$0.413

Chronological block delta vs A6.22: 5 positive, 2 zero, 1 negative. The negative block is small (-$0.582).

## Research verdict

**EMA can identify damaging Friday failures, but as structure, not as a simple cross.** The strongest practical structure observed is the 45m bearish EMA stack+widen state. Using it as an earlier risk-warning layer and retaining the proven 60m fallback improves economics while preserving all 138 entries and the 60.87% WR.

Current provisional Friday research metrics after A6.33:
- N138
- WR 60.87%
- PnL +$141.025
- PF1.720
- max DD $46.318
- LS4
- validation +$1.553

## Caution

A6.33 is **not fresh OOS proof**. The EMA45 structure was identified during A6.32 on this same historical dataset, and its validation behavior was visible before A6.33 architecture was assembled. Therefore validation +$1.553 is supportive robustness evidence, not pristine untouched OOS. Do not retune EMA periods/timing/thresholds further on these same 138 Fridays. Correct next proof is fresh unseen Fridays or frozen transfer to another comparable temporal BUY setup.
