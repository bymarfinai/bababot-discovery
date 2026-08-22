# BTC London -> New York F85 Current State Snapshot

Saved: 2026-08-22

## Frozen structural model
- Instrument: BTCUSDT perpetual
- Research clock: raw 5m
- Session structure: previous London High/Low frozen before New York
- Directional detector: B27Q London -> New York LONG K1 OPP0
- Entry window: after causal leave from Touch High #1 and before Touch High #2
- H2 is a milestone, not TP

## Entry rule comparison

### Blind F85
- Major partitions: 149 trades
- Fixed-E20 pooled WR 68.5%, PF 1.40, expectancy +$0.60/trade, net +$89.68

### Early Reclaim
- F85 touched; first causal 5m reclaim; enter next 5m open if still pre-H2
- Major partitions: 118 trades
- Fixed-E20 pooled WR 71.2%, PF 1.47, expectancy +$0.65/trade, net +$76.51
- Current balance candidate; frozen gate not passed

### Same-Bar Rejection
- Same 5m candle that first touches F85 closes back above F85; next-open entry if causal/pre-H2
- Major partitions: 68 trades
- Fixed-E20 pooled WR 73.5%, PF 1.70, expectancy +$0.91/trade, net +$61.80
- Diagnostic only; sample too small for promotion

## Current working exit rule — B27AC hybrid
User-selected working direction for further research:
1. Before E20: retain F35 completed-5m-close invalidation.
2. E20 = London High + 0.20 * London range.
3. E20 is a minimum profit milestone, not a final TP.
4. Once E20 has been reached, the full position remains open from the next causal 5m bar and E20 becomes the minimum profit floor.
5. As price continues upward, the floor may ratchet upward only when a new causally confirmed strict 3-bar 5m pivot low is above the current floor.
6. The floor never moves downward.
7. As long as price keeps rising and does not touch/breach the active floor, the position stays open; there is no fixed upper TP.
8. If price retraces to the active resting floor, close there; if it gaps/opens below the floor, close at the actual open.
9. If still open at New York session end, close at the first 5m open at 20:00 UTC.

B27AC pooled Early Reclaim comparison:
- Fixed E20: WR 71.2%, PF 1.47, expectancy +$0.65/trade, total +$76.51
- Hybrid: WR 66.1%, PF 1.62, expectancy +$0.88/trade, total +$103.29
- Pooled improvement +$26.78
- Formal B27AC primary gate NOT PASSED because external expectancy declined, despite development and validation improving.

## Status
- The B27AC hybrid above is the saved current working exit rule for subsequent research.
- It is not promoted to live BBC.
- Live BBC remains unchanged unless explicitly requested.
