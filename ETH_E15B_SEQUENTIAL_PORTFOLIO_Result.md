# ETH E15B — Sequential / One-Position Portfolio Replay

**Status:** Development-only. OOS CLOSED. No live authorization.

## Frozen question

Do the two formal E15A max-6h LONG components remain economically valid after overlapping anchor signals and cross-hour position overlap are removed by a realistic one-position-at-a-time replay?

## Frozen inputs

- 01:00–02:00 WIB: `RV_HIGH__RANGE_MID / LB240 / H360`.
- 03:00–04:00 WIB: `RV_HIGH__RANGE_MID / LB360 / H240`.
- Same ETHUSDT 5m source, Development partition (2022/2023/2024), $500 notional and $0.75 fee as E12/E15A.
- Entry policy: chronological earliest eligible signal while flat; every later signal before the active trade exits is blocked.
- No future knowledge, no signal replacement, no OOS exposure.

Raw ETHUSDT 5m coverage: **100.0000%**.

## Replay results

| Replay | Source | Accepted | Blocked | Blocked % | WR | Net | Exp | PF | DD | LS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 01WIB_H6_FLAT_ONLY | 247 | 110 | 137 | 55.47% | 59.09% | $+130.37 | $+1.19 | 1.479 | $+36.32 | 6 |
| 03WIB_H4_FLAT_ONLY | 250 | 107 | 143 | 57.20% | 61.68% | $+188.19 | $+1.76 | 1.844 | $+73.28 | 5 |
| 01WIB_H6_PLUS_03WIB_H4_FLAT_ONLY | 497 | 154 | 343 | 69.01% | 60.39% | $+203.83 | $+1.32 | 1.525 | $+45.13 | 3 |
| INDEPENDENT_POOLED_DIAGNOSTIC | 497 | 497 | 0 | 0.00% | 59.56% | $+859.82 | $+1.73 | 1.869 | $+111.79 | 8 |

## Combined sequential year stability

| Year | N | WR | Net | Exp | PF | DD | LS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 46 | 56.52% | $+58.87 | $+1.28 | 1.352 | $+45.13 | 3 |
| 2023 | 48 | 60.42% | $+59.25 | $+1.23 | 1.592 | $+17.18 | 3 |
| 2024 | 60 | 63.33% | $+85.71 | $+1.43 | 1.710 | $+30.84 | 3 |

## Portfolio mechanics

Accepted contribution: **01WIB_H6=110**, **03WIB_H4=44**.
Blocked signals: **01WIB_H6=137**, **03WIB_H4=206**.

## Frozen preservation gate

Combined sequential replay requires N>=90, WR>=55%, net>0, expectancy>=+$0.50/trade, PF>=1.20, DD<= $125, max loss streak<=8, plus each Development year N>=20 with positive expectancy and PF>1.0.

## Verdict

**ETH_E15B_SEQUENTIAL_SURVIVES**

This is a preservation test of the already-selected E15A components, not a new optimization search.
Research/shadow only. OOS remains closed and nothing here authorizes live deployment.
