# ETH E16A — 02:00–03:00 WIB LONG Native Character Rediscovery

**Development-only. OOS CLOSED. No live authorization.**

## Preregistered question

Can 02:00–03:00 WIB produce a robust native ETH LONG character after timing calibration while preserving the exact E12 90-rule grammar and formal gates?

ETHUSDT 5m Development coverage: **100.0000%**.

## Stage 0 — E15A baseline reproduction

Reproduced: **DRIVE_DOWN__STR_B60_80 / LB120 / H360**.
N 311, WR 60.13%, net $+258.70, exp $+0.83, PF 1.313, DD $+111.90, LS 8.
Gates: anchor=True, pooled=True, era=False. 2024 WR 54.46%, exp $-0.18, PF 0.933.

## Stage 1 — refined timing grid

Grid: **8,100 candidates** = 10 lookbacks × 9 holds × 90 rules.
Formal full-gate passers: **2**.

### Selected Development representative

**RV_HIGH__RANGE_MID / LB150 / H300**
- Formal status: **PASS**
- N 230, WR 59.57%, net $+233.02, exp $+1.01, PF 1.345, DD $+120.15, LS 7
- anchors supportive/evaluable: 3/4
- gates: anchor=True, pooled=True, era=True

### Development-year stability

| Year | WR | Net | Exp | PF |
|---:|---:|---:|---:|---:|
| 2022 | 60.98% | $+107.71 | $+1.31 | 1.390 |
| 2023 | 58.11% | $+50.75 | $+0.69 | 1.306 |
| 2024 | 59.46% | $+74.57 | $+1.01 | 1.319 |

## Executable-opportunity diagnostic

The formal gate above is still the original pooled E12 gate. This replay is diagnostic only and removes within-hour anchor overlap chronologically.

Source signals **230** → accepted **114**, blocked **116** (50.43%).
Executable WR 58.77%, net $+105.80, exp $+0.93, PF 1.303, DD $+59.38, LS 4.

| Year | Executable N | WR | Net | Exp | PF | DD | LS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 38 | 60.53% | $+37.36 | $+0.98 | 1.283 | $+34.15 | 3 |
| 2023 | 36 | 52.78% | $+12.09 | $+0.34 | 1.130 | $+52.50 | 4 |
| 2024 | 40 | 62.50% | $+56.35 | $+1.41 | 1.453 | $+59.38 | 4 |

## Verdict

**ETH_E16A_02_03WIB_NATIVE_CHARACTER_FOUND**

No gate was relaxed and no OOS data was exposed for selection. All grids, passers, near-misses, and executable-overlap diagnostics are persisted with this result.
Research/shadow only; this does not authorize live trading.
