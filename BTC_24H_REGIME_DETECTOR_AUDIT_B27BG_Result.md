# B27BG — BTC 24H Causal Regime Detector Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** This experiment audits regime identity/persistence only. No future return, liquidity direction, LONG/SHORT mapping, entry, stop, target, fee, WR, PF, or PnL was used.

Frozen B27BE result SHA256 observed during audit: `c4df0f7d5fb1afe71a935f8b0a094668653eb4c73f3bd4b60dc7291d7a8b8895`.

## Major-partition detector summary

| Partition | State | Intervals | Occupancy | Episodes | Median episode | P75 | P90 | Max | Next-state persistence | Changes/week |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | BULL | 2264 | 51.6% | 168 | 7.0 bars / 28h | 16.5 | 38.0 | 75 | 92.6% | 5.35 |
| external | BEAR | 1007 | 23.0% | 120 | 6.0 bars / 24h | 11.2 | 19.0 | 72 | 88.2% | 5.35 |
| external | SIDEWAYS | 1114 | 25.4% | 272 | 2.0 bars / 8h | 4.0 | 9.9 | 42 | 75.6% | 5.35 |
| development | BULL | 2943 | 44.8% | 268 | 6.0 bars / 24h | 15.0 | 29.0 | 73 | 90.9% | 6.60 |
| development | BEAR | 2857 | 43.4% | 297 | 5.0 bars / 20h | 13.0 | 24.4 | 62 | 89.6% | 6.60 |
| development | SIDEWAYS | 776 | 11.8% | 468 | 1.0 bars / 4h | 2.0 | 3.0 | 5 | 39.7% | 6.60 |
| reference_validation | BULL | 1483 | 43.0% | 171 | 4.0 bars / 16h | 10.0 | 26.0 | 52 | 88.5% | 7.41 |
| reference_validation | BEAR | 1450 | 42.0% | 155 | 5.0 bars / 20h | 13.0 | 22.0 | 61 | 89.4% | 7.41 |
| reference_validation | SIDEWAYS | 517 | 15.0% | 284 | 1.0 bars / 4h | 2.0 | 3.0 | 19 | 45.1% | 7.41 |
| POOLED_MAJOR | BULL | 6690 | 46.4% | 607 | 6.0 bars / 24h | 13.5 | 30.0 | 75 | 90.9% | 6.42 |
| POOLED_MAJOR | BEAR | 5314 | 36.9% | 572 | 5.0 bars / 20h | 12.0 | 22.0 | 72 | 89.3% | 6.42 |
| POOLED_MAJOR | SIDEWAYS | 2407 | 16.7% | 1024 | 2.0 bars / 8h | 2.0 | 4.0 | 42 | 57.5% | 6.42 |

## Pooled-major transition matrix

| From -> To | BULL | BEAR | SIDEWAYS |
|---|---:|---:|---:|---:|
| BULL | 90.9% | 1.1% | 8.0% |
| BEAR | 1.5% | 89.3% | 9.2% |
| SIDEWAYS | 21.9% | 20.6% | 57.5% |

## Transition / noise diagnostics

- Pooled state changes: **2,202**.
- Direct BULL<->BEAR changes: **155** (7.0% of changes).
- Directional -> SIDEWAYS changes: **1,023** (46.5% of changes).
- One-interval flip-backs A->B->A: **459/2,202 = 20.8%** under the preregistered denominator.
- Maximum major-partition occupancy drift for any state: **20.5 percentage points**.

## Weekday/weekend occupancy — descriptive only

| Day type | BULL | BEAR | SIDEWAYS |
|---|---:|---:|---:|
| WEEKDAY | 46.5% | 35.7% | 17.8% |
| WEEKEND | 46.2% | 39.8% | 13.9% |

## Frozen detector-quality gate

- Every state >=100 intervals in every major partition: **PASS**.
- BULL and BEAR persistence >=60% in every major partition: **PASS**.
- Pooled flip-back rate <=20%: **FAIL** (20.8%).
- Pooled median BULL episode >=2 bars: **PASS** (6.0).
- Pooled median BEAR episode >=2 bars: **PASS** (5.0).
- Major-partition occupancy drift <=20pp: **FAIL** (20.5pp).

**Frozen verdict: B27BG_REGIME_DETECTOR_NEEDS_REDESIGN.**

B27BG does not determine trade direction. If this detector is accepted, the next experiment must separately study directional behavior inside each frozen regime before any entry-location research.

Research only. Live BBC unchanged.
