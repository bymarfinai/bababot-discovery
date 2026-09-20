# BNB B38-S20 — Post-Entry Failure Character Preregistration

## Objective
Find a causal post-entry failure character that identifies frozen E2 trades deteriorating before the full structural -1R stop is reached.

This stage is diagnostic. It does not alter the E2 detector, entry, initial structural SL, or TP1.

## Frozen upstream
- E2 signature:
  `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
- Executable E2 population:
  - DEV 440 = 325 WIN / 115 LOSS
  - REF 272 = 201 WIN / 71 LOSS
- Wide-SL Q4 cut:
  `baseline_sl_pct > 0.017122292197580727`
  - DEV 110
  - REF 50

## Structural state reconstruction
For every E2 plan, reconstruct the exact frozen sequence:
`reclaim -> hold -> local break -> entry`

Hard parity rule:
- reconstructed entry timestamp and price must equal the frozen E2 entry.

Levels already known at entry:
- breakout threshold = max(reclaim high, hold high)
- hold close
- reclaim close
- H1 demand high
- H1 demand low
- original structural SL = first-touch-to-entry low

## Candidate post-entry failure states
Signals are evaluated only after the E2 entry bar has closed.

1. **TOUCH_BREAK_LEVEL**
   - first later 5m bar whose low reaches the frozen breakout threshold.

2. **CLOSE5_BELOW_BREAK_LEVEL**
   - first completed 5m close below the breakout threshold.

3. **CLOSE5_BELOW_HOLD_CLOSE**
   - first completed 5m close below the frozen hold-bar close.

4. **CLOSE5_BELOW_RECLAIM_CLOSE**
   - first completed 5m close below the frozen reclaim-bar close.

5. **CLOSE5_BELOW_DEMAND_HIGH**
   - first completed 5m close below the H1 demand upper boundary.

6. **CLOSE15_BELOW_DEMAND_HIGH**
   - first completed 15m close below the H1 demand upper boundary.

No numeric threshold is optimized.

## Causality / ambiguity
A signal is credited only if it occurs before frozen TP1 and before the original structural SL.
If TP1 or structural SL trades in the same 5m bar as a candidate signal, that observation is marked ambiguous and not credited as a clean predictive signal.

## Required diagnostics
For DEV and REF, both ALL E2 and wide-SL Q4:
- signal coverage among baseline WIN and LOSS
- loss-capture rate
- winner false-exit rate
- precision: fraction of clean signals that belong to eventual baseline LOSS
- median minutes from signal to original SL for captured losses
- median minutes from signal to later TP1 for false-exited winners
- realized R at signal using the original risk denominator
- counterfactual economics if a trade exits at the first clean signal close/touch while unsignaled trades keep the frozen baseline outcome

## Decision boundary
No state is promoted from DEV alone.
A useful failure character must:
- capture a meaningful share of baseline losses,
- preserve most baseline winners in both DEV and REF,
- occur materially before the original SL,
- and improve economics in both periods without changing the frozen detector.
