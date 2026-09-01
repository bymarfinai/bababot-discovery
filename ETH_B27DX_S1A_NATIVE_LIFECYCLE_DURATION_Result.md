# ETH B27DX — S1A Native Lifecycle Duration Discovery — Result

ETH raw 5m coverage: **100.0000%**.

B27DX causal grammar, F90/F85/F80 probes, E20 target, F35 completed-close invalidation, fee/notional, and historical partitions are frozen. Only reference duration and execution lifespan vary.

## Supported structural cells

| Anchor | Ref | Horizon | Ref start | Dev + | Dev PF | Ext + | Val + | Raw opp/week |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 09:30 | 120m | 390m | 07:30 | 2/3 | 1.27 | 2/3 | 3/3 | 0.549 |
| 09:30 | 120m | 420m | 07:30 | 2/3 | 1.24 | 2/3 | 3/3 | 0.549 |
| 09:30 | 330m | 360m | 04:00 | 3/3 | 1.43 | 3/3 | 3/3 | 0.607 |
| 09:30 | 330m | 390m | 04:00 | 3/3 | 1.50 | 3/3 | 3/3 | 0.620 |
| 09:30 | 330m | 420m | 04:00 | 3/3 | 1.46 | 3/3 | 3/3 | 0.626 |
| 16:00 | 240m | 300m | 12:00 | 2/3 | 1.15 | 3/3 | 3/3 | 0.377 |
| 16:00 | 240m | 360m | 12:00 | 2/3 | 1.18 | 3/3 | 3/3 | 0.383 |
| 16:00 | 240m | 390m | 12:00 | 2/3 | 1.29 | 3/3 | 3/3 | 0.396 |
| 16:00 | 240m | 420m | 12:00 | 2/3 | 1.33 | 3/3 | 3/3 | 0.409 |
| 16:00 | 300m | 240m | 11:00 | 2/3 | 1.12 | 3/3 | 3/3 | 0.370 |
| 16:00 | 300m | 300m | 11:00 | 2/3 | 1.30 | 3/3 | 3/3 | 0.377 |
| 16:00 | 300m | 360m | 11:00 | 2/3 | 1.17 | 3/3 | 3/3 | 0.390 |
| 16:00 | 300m | 390m | 11:00 | 2/3 | 1.28 | 3/3 | 2/3 | 0.396 |
| 16:00 | 300m | 420m | 11:00 | 2/3 | 1.41 | 3/3 | 2/3 | 0.409 |
| 16:00 | 330m | 240m | 10:30 | 2/3 | 1.19 | 3/3 | 3/3 | 0.364 |
| 16:00 | 330m | 300m | 10:30 | 2/3 | 1.33 | 2/3 | 3/3 | 0.370 |
| 16:00 | 330m | 360m | 10:30 | 2/3 | 1.19 | 3/3 | 3/3 | 0.377 |
| 16:00 | 330m | 390m | 10:30 | 2/3 | 1.30 | 2/3 | 3/3 | 0.383 |
| 16:00 | 330m | 420m | 10:30 | 2/3 | 1.45 | 3/3 | 3/3 | 0.396 |
| 16:00 | 360m | 300m | 10:00 | 2/3 | 1.25 | 3/3 | 3/3 | 0.351 |
| 16:00 | 360m | 360m | 10:00 | 2/3 | 1.13 | 3/3 | 3/3 | 0.358 |
| 16:00 | 360m | 390m | 10:00 | 2/3 | 1.17 | 2/3 | 3/3 | 0.364 |
| 16:00 | 360m | 420m | 10:00 | 2/3 | 1.33 | 3/3 | 3/3 | 0.383 |

## Connected duration components

| Anchor | Component | Cells | Refs | Horizons | Median raw opp/week | Native 2D family |
|---:|---:|---:|---:|---:|---:|---|
| 09:30 | 1 | 2 | 120 | 390,420 | 0.549 | NO |
| 09:30 | 2 | 3 | 330 | 360,390,420 | 0.620 | NO |
| 16:00 | 1 | 18 | 240,300,330,360 | 240,300,360,390,420 | 0.380 | YES |

## Cross-anchor overlap

- R330/X360: 09:30 **0.607/wk** + 16:00 **0.377/wk** = raw two-anchor **0.984/wk**.
- R330/X390: 09:30 **0.620/wk** + 16:00 **0.383/wk** = raw two-anchor **1.003/wk**.
- R330/X420: 09:30 **0.626/wk** + 16:00 **0.396/wk** = raw two-anchor **1.022/wk**.

## Legacy BTC-derived benchmark

- 09:30 R330/X390: supported **YES**, raw opportunity density **0.620/wk**.
- 16:00 R330/X390: supported **YES**, raw opportunity density **0.383/wk**.

## Decision

**Status: ETH_S1A_NATIVE_LIFECYCLE_SUPPORTED**

Opportunity density is diagnostic only and never overrides the historical support gates.
No entry/TP/stop/runner/leverage optimization and no live BBC changes were made.
