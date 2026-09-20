# BNB B38-S19 — Wide-SL Post-Confirmation Entry Audit Preregistration

## Objective
Test whether the frozen E2 wide-SL problem is caused by entering too far above the structural invalidation, rather than by the invalidation itself.

## Frozen upstream
- E2 signature: `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
- Wide-SL definition from S17/S18:
  `baseline_sl_pct > 0.017122292197580727`
- Wide population:
  - DEV 110
  - REF 50
- Detector remains: `reclaim -> hold -> local break`
- Structural invalidation remains the original first-touch-to-entry low.
- TP remains frozen causal TP1.

## Principle
The E2 detector must complete first. No early anticipatory entry is allowed.
Only after the local-break confirmation closes may a resting limit order be placed at a structural level that was already known at confirmation.

## Causal entry candidates
1. **MARKET_BREAK_CLOSE**
   - Existing E2 baseline entry.

2. **LIMIT_BREAK_LEVEL_RETEST**
   - Retest of the exact breakout threshold `max(reclaim_high, hold_high)`.

3. **LIMIT_HOLD_CLOSE_RETEST**
   - Retest of the completed HOLD bar close.

4. **LIMIT_RECLAIM_CLOSE_RETEST**
   - Retest of the completed reclaim bar close.

5. **LIMIT_DEMAND_HIGH_RETEST**
   - Retest of the H1 demand-zone upper boundary.

Orders become active only on the first 5m bar strictly after E2 confirmation.
No same-confirmation-bar fill is permitted.

## Fill/outcome discipline
- A candidate is available only when its level is below the baseline market entry and above the frozen structural SL.
- Limit fill must occur before frozen TP1 or frozen SL.
- If fill and TP/SL are touched in the same 5m bar, the trade is marked ambiguous because intrabar ordering is unknowable.
- After an unambiguous fill, TP1 and original structural SL remain unchanged.

## Required outputs
For DEV and REF:
- candidate availability
- fill rate
- median entry improvement %
- median risk compression %
- baseline WINs filled and retained
- baseline WINs missed due no fill
- baseline LOSSES avoided due no fill
- post-fill W/L/WR
- median winner R / expectancy / total R
- false-stop count (should remain zero because SL is unchanged)
- full E2 portfolio result if wide-Q4 is replaced by each retest policy, with nonfills treated as no-trade (0R)

Also report annual stability.

## Decision boundary
S19 is an entry-location diagnostic only.
No retest entry is promoted unless its fill/retention/economics survive DEV and REF without changing the detector or structural invalidation.
