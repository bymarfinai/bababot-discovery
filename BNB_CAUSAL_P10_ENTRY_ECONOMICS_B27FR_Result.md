# BNB Causal P10 Entry Economics — B27FR

- Raw loader coverage: 100.0000%
- Frozen normalized universe: 2022-01-02 through 2024-12-31 inclusive
- Complete sessions: 1095
- Frozen geometry: reference 01:00–05:00 WIB; execution 05:00–10:00 WIB
- B27FQ reproduction gate: PASS (167 causal leaves, 142 H2)
- Structural H2/leave rate: 85.03% — **not trading WR**
- P10 and geometry were frozen before this runner; no holdout data used

## Causal signal and execution funnel

- Causal leaves examined: 167
- Skipped because H2 already occurred on first post-leave bar: 32
- Skipped because completed first close was outside P10 band: 107
- Missing first post-leave bar: 0
- P10 causal signals after completed first post-leave bar: 28
- Skipped: no next bar for entry: 0
- Skipped: next-open entry >= H: 0
- Entered trades: 28
- Structural H target touched after entry: 25/28 = 89.3%
- Unambiguous TARGET_H exits: 25/28 = 89.3%

## Exit reasons

| Exit reason | Count | Share |
|---|---:|---:|
| TARGET_H | 25 | 89.3% |
| SESSION_END_1000 | 2 | 7.1% |
| CLOSE_BELOW_L_NEXT_OPEN | 1 | 3.6% |

## Trading economics

- Notional: $500/trade
- Fee: 8 bps round trip ($0.40 on $500 before price PnL effects)
- Slippage stress is adverse per side and applied to both entry and exit
- **Trading WR below means net PnL > 0 after fee and stated slippage.**

| Slippage/side | N | WR | PF | Expectancy $ | Net $ | Avg win $ | Avg loss $ | Max loss streak |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 bps | 28 | 42.9% | 0.91 | -0.02 | -0.64 | 0.55 | -0.45 | 6 |
| 2 bps | 28 | 35.7% | 0.41 | -0.22 | -6.24 | 0.43 | -0.59 | 8 |
| 5 bps | 28 | 21.4% | 0.12 | -0.52 | -14.64 | 0.33 | -0.76 | 8 |
| 10 bps | 28 | 7.1% | 0.02 | -1.02 | -28.63 | 0.23 | -1.12 | 13 |

## Yearly stability — fee included, 0 bps slippage

| Year | N | WR | PF | Expectancy $ | Net $ | Max loss streak |
|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 8 | 62.5% | 4.20 | 0.29 | 2.30 | 2 |
| 2023 | 11 | 27.3% | 0.36 | -0.32 | -3.57 | 6 |
| 2024 | 9 | 44.4% | 1.67 | 0.07 | 0.63 | 2 |

## Frozen classification

**ECONOMIC_EDGE_NOT_SUPPORTED**

Classification gates were preregistered before the runner was committed.
This is development-sample economics only. It is not independent holdout validation and does not authorize live trading.

## Status

`B27FR_BNB_CAUSAL_P10_ENTRY_ECONOMICS_COMPLETE_ECONOMIC_EDGE_NOT_SUPPORTED`
