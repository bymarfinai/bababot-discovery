# SOL Options Wall Forward Validation V1 — Result

**Status: FORWARD_TOUCH_OBSERVED**

## Completed prospective regime #1

- Regime start: 2026-09-22T02:29:31.999Z
- Frozen horizon: 240 minutes
- Horizon end: 2026-09-22T06:29:31.999Z
- SOLUSDT observed range: 115.54–118.09
- Primary lower wall: 116
- Primary upper wall: 120
- Wall levels evaluated: 6
- First-touch observations: 1

### Lower wall 116

First touch occurred at **2026-09-22T05:18:00Z**.

Post-touch path from the pre-recorded 116 wall:

| Horizon | Favorable excursion | Adverse excursion | Close displacement | Favorable share of total excursion |
|---|---:|---:|---:|---:|
| 15m | +0.190% | -0.397% | -0.345% | 0.324 |
| 30m | +0.922% | -0.397% | +0.853% | 0.699 |
| 60m | +1.017% | -0.397% | +0.603% | 0.720 |
| End | +1.017% | -0.397% | +0.517% | 0.720 |

Symmetric first-passage outcomes:

- ±0.25%: **ADVERSE_FIRST**
- ±0.50%: **FAVORABLE_FIRST**
- ±1.00%: **FAVORABLE_FIRST**

The observed anatomy was therefore: shallow penetration below the wall first, followed by a larger upward reaction. This is compatible with a sweep/rejection interpretation, but N=1 is not evidence that the level is generally predictive.

The remaining recorded walls (110, 100, 120, 122, 130) were not touched during the frozen 240-minute horizon and are not counted as wins or losses.

## New prospective regime

Snapshot **SOL_OPT_V1_20260923043811000** created a new map regime because the expiry tuple and ranked walls changed:

- Spot: 119.49133106
- Expiries: 260923, 260924, 260925
- Lower walls: 116, 112, 110
- Upper walls: 120, 130, 140
- Lower top-1 116 score: 0.265565
- Upper top-1 120 score: 0.705237

The new regime is still accumulating forward data.

## Current interpretation

1. Options wall location passed the initial two-snapshot stability sanity check.
2. The first completed causal wall touch produced a sweep-below-then-rebound path at 116.
3. This is anatomically promising for the real-liquidity hypothesis, but one touch is far below the evidence needed for promotion.
4. IV confluence remains descriptive only; it is not a trading gate.
5. Historical SOL trades before the first options snapshot remain ineligible for options-map attribution.

No READY_TO_TRADE conclusion is permitted from this sample.
