# BNB B38-S13 — E2 Path & Real-Room Audit Preregistration

## Scope
This stage executes only Steps 1–3:
1. Freeze the exact B38-S10/S11 E2 detector and entry character.
2. Audit post-entry path anatomy for every frozen E2 plan.
3. Map causal structural/liquidity room that was already knowable at entry.

## Frozen baseline
- Detector/entry: `reclaim -> 1 hold -> local break -> entry`
- Structural SL: first-touch-to-entry low (same B38-S11 baseline)
- Baseline target: causal structural TP1 (same B38-S11/S12)
- Expected parity:
  - DEV: 440 plans, 325 WIN, 115 LOSS
  - REF: 272 plans, 201 WIN, 71 LOSS

Any parity drift aborts the run.

## Measurements only — no optimization
For every E2 plan:
- MFE and MAE at 4h, 12h, 24h, capped by the first structural SL touch.
- MFE before structural SL, peak timing, and post-peak giveback.
- TP1 capture fraction and missed room.
- Excursion thresholds: +0.25R, +0.50R, +1.00R, +1.50R, +2.00R.
- Causal target availability, distance, hit-before-SL, and time-to-hit for:
  TP1, TP2, TP3, expansion high, nearest confirmed H1 pivot high, and nearest major objective.

The SL bar is excluded from pre-stop MFE/MAE because intrabar high/low ordering is unknowable.

## Boundary
No new filter, adaptive TP, SL, or entry rule may be promoted in B38-S13.
The output is diagnostic evidence for the next stage only.
