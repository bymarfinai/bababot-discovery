# ETH B27DX — S5A Zone-Native Entry Freeze + Target Geometry — Result

ETH raw 5m coverage: **100.0000%**.

Frozen lifecycle: **R300/X360**. Each clock uses its S2-predeclared zone-native entry. F35 completed-close invalidation remains fixed. Only target extension varies.

## Zone-native target families

| Clock | Entry | Robust targets | Selected family | Representative | Dev WR | Dev PF | Ext WR | Ext PF | Val WR | Val PF | Dev opp/wk |
|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 05:00 | F80 | E15,E20,E25,E30,E35,E40 | E15→E20→E25→E30→E35→E40 | E30 | 56.9% | 1.38 | 55.6% | 2.11 | 64.3% | 1.52 | 0.370 |
| 09:00 | F80 | E10,E15,E20,E25,E30,E35,E40 | E10→E15→E20→E25→E30→E35→E40 | E25 | 64.6% | 1.33 | 58.9% | 1.02 | 65.7% | 1.55 | 0.613 |
| 10:00 | F75 | E05,E10,E15,E20,E25,E30,E35,E40 | E05→E10→E15→E20→E25→E30→E35→E40 | E25 | 58.8% | 1.25 | 65.8% | 1.72 | 56.1% | 1.40 | 0.620 |
| 16:00 | F90 | E20,E25 | E20→E25 | E25 | 62.3% | 1.36 | 55.0% | 1.55 | 56.4% | 1.07 | 0.390 |

## Full robust target map

| Clock | Entry | Target |
|---:|---:|---:|
| 05:00 | F80 | E15 |
| 05:00 | F80 | E20 |
| 05:00 | F80 | E25 |
| 05:00 | F80 | E30 |
| 05:00 | F80 | E35 |
| 05:00 | F80 | E40 |
| 09:00 | F80 | E10 |
| 09:00 | F80 | E15 |
| 09:00 | F80 | E20 |
| 09:00 | F80 | E25 |
| 09:00 | F80 | E30 |
| 09:00 | F80 | E35 |
| 09:00 | F80 | E40 |
| 10:00 | F75 | E05 |
| 10:00 | F75 | E10 |
| 10:00 | F75 | E15 |
| 10:00 | F75 | E20 |
| 10:00 | F75 | E25 |
| 10:00 | F75 | E30 |
| 10:00 | F75 | E35 |
| 10:00 | F75 | E40 |
| 16:00 | F90 | E20 |
| 16:00 | F90 | E25 |

## BTC benchmark diagnostic

- BTC B27DX LONG final: WR 71.9%, PF 2.22, expectancy +$1.26/trade.
- S5A freezes target representatives by family topology, not by maximum performance.

## Decision

**Status: ETH_S5A_ALL_ZONES_TARGET_FAMILIES_SUPPORTED**

- No per-clock entry reselection, stop, runner, leverage, lifecycle, clock, or live-code changes were made.
