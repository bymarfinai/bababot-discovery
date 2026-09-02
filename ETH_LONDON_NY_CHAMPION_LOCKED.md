# ETH London -> New York Champion — LOCKED

**Status: LOCKED RESEARCH CHAMPION**

This file freezes the current best ETH London -> New York setup so later experiments do not silently redefine the benchmark.

## Champion setup

- Pair: **ETHUSDT perpetual**
- Direction: **LONG**
- Data: raw **5m**
- Session lineage: **London -> New York**
- London range: **08:00-13:30 UTC** / **15:00-20:30 WIB**
- NY execution window: **13:30-20:00 UTC** / **20:30-03:00 WIB**
- Frozen range:
  - `L` = London low
  - `H` = London high
  - `R = H - L`

## Entry grammar

1. First attack/arrival to London High (`K1`).
2. Causal leave after the K1 episode.
3. Price retraces to/touches `F90 = L + 0.90R` before H2.
4. EARLY_RECLAIM confirmation:
   - the F90-touch candle may confirm if its completed 5m close is `> F90`; otherwise
   - use the first later completed 5m close `> F90` before H2 / close below L / session end.
5. Entry executes at the **next raw 5m open** after confirmation.

## Target and invalidation

- Profit target: `E15 = H + 0.15R`.
- Hard invalidation: first completed 5m close `< F50`, where `F50 = L + 0.50R`.
- Session-end time exit remains active if neither target nor invalidation has completed first.

## H2-state management — M14

- `H2` = first later return/arrival to London High after the causal leave, defined by candle `high >= H`; a close above H is not required.
- `F75 = L + 0.75R`.
- A close below F75 **before H2** is **not** an exit condition.
- If H2 has already occurred and a later completed 5m candle closes `< F75`, treat this as failed continuation.
- Execute the conditional exit at the **next raw 5m open**.
- If this condition never occurs, keep the original E15 / F50 lifecycle.

### Live-readable rule

`F90 EARLY_RECLAIM LONG -> E15 target / F50 hard invalidation; after H2 only, completed close < F75 -> exit next 5m open.`

## Locked cohort

Exact M5 F90 EARLY_RECLAIM executed cohort:

- External: **39 setups**
- Development: **41 setups**
- Reference validation: **15 setups**
- Pooled major: **95 setups**

## Champion economics — M14 E15

| Partition | N | WR | PF | Expectancy | Net | 5bps WR | 5bps PF | 5bps Net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| External | 39 | 79.5% | 2.03 | +$1.44 | +$56.26 | 76.9% | 1.75 | +$44.01 |
| Development | 41 | 70.7% | 1.19 | +$0.27 | +$10.94 | 65.9% | 0.96 | -$2.54 |
| Reference validation | 15 | 73.3% | 1.74 | +$1.01 | +$15.11 | 73.3% | 1.46 | +$10.36 |
| **Pooled major** | **95** | **74.7%** | **1.61** | **+$0.87** | **+$82.31** | **71.6%** | **1.35** | **+$51.83** |

## M14 conditional-exit composition

Across pooled major:

- F75 breaches observed: **32**
- PRE_H2 breaches: **24**
- H2_SEEN breaches: **8**
- M14 conditional exits: **8**
- Of those 8 exits: **7 baseline losers**, **1 baseline winner**

Development specifically:

- F75 breaches: **17**
- PRE_H2: **12**
- H2_SEEN: **5**
- Conditional exits: **5**
- **5/5 were baseline losers**
- **0 baseline winners were cut**

## Research status

- M14 status: **ETH_LONDON_NY_M14_H2_STATE_CONDITIONAL_EXIT_SUPPORTED**.
- M15 tested the already-supported M14 management across E05/E10/E15 and found **no target that passed the stricter M15 cross-partition + Development 5bps screen**.
- M15 does **not** revoke the M14 champion. E15 remains the best current target and this file remains the locked benchmark until a future experiment explicitly beats it under a preregistered comparison.

## Benchmark discipline

Future ETH experiments must:

1. Keep this champion unchanged as a benchmark control.
2. Report deltas versus this locked setup.
3. Never replace the champion based on structural telemetry alone; any replacement must reach economic testing.
4. Avoid fine parameter sweeps around F90/F75/F50/E15 unless independently justified and preregistered.
5. Preserve the distinction between universal causal grammar and pair-native habitat/lifecycle discovery.

Research only. Live Baba Bot rules remain unchanged unless separately promoted and implemented.