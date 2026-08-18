# Sunday T-Method — ST4 to ST11

**Status: COMPLETE — EMA/FastMR/RunnerRecovery milestones rebuilt for Sunday; live BBC untouched.**

## Reset base
- Parent: WR **47.48%**, PnL **$+63.60**, PF **1.14**.
- ST0-ST3 price-path protection was rejected, so it is NOT carried forward.

## ST4 EMA forensic at +1.00% favorable hinge
- Hinge trades 76 = 62 eventual wins / 14 losses.
- EMA20 distance median: winners 0.555% vs losers 0.618%.

## ST5-ST6 broad EMA confirmation

| Rule | Actions | WR | PnL | D PnL | V PnL |
|---|---:|---:|---:|---:|---:|
| 2C_ABOVE_EMA7 | 67 | 56.12% | $-38.61 | $-17.24 | $-21.37 |
| 1C_ABOVE_EMA20 | 60 | 56.12% | $-22.78 | $-7.10 | $-15.68 |
| 2C_ABOVE_EMA20 | 60 | 54.68% | $-37.19 | $-17.28 | $-19.91 |

## ST7-ST9 Sunday FastMR

Rule: after +1.00% MFE, require hinge EMA20 overextension; if within 120m close gives back to <=+0.60%, arm +0.40% lock while original TP/SL remain.

| EMA20 overextension | Actions D/V | WR | PnL | D PnL | V PnL |
|---:|---:|---:|---:|---:|---:|
| 0.40% | 14/7 | 53.96% | $+60.29 | $+44.94 | $+15.35 |
| 0.60% | 10/5 | 52.52% | $+68.17 | $+56.69 | $+11.49 |
| 0.80% | 2/2 | 49.64% | $+83.48 | $+71.90 | $+11.58 |
| 1.00% | 0/1 | 47.48% | $+63.40 | $+53.90 | $+9.50 |

Selected discovery threshold **0.60% below EMA20**.
- FastMR: WR **52.52%**, PnL **$+68.17**, PF **1.16**, actions 15, blocks 6/8.
- D: 53.01%, $+56.69; V: 51.79%, $+11.49.

## ST10-ST11 EMA7 runner recovery
Before +0.40 lock is touched: if completed 5m tests/gets above EMA7 but closes back below EMA7 while SELL progress remains >=+0.60%, cancel lock next open and restore original runner.
- Recovery actions **6**.
- FastMR $+68.17 -> recovery **$+65.04** (delta **$-3.13**).
- WR **50.36%**, PF **1.15**, blocks **6/8**.
- D: 51.81%, $+56.88; V: 48.21%, $+8.16.

## Guardrail
Milestone logic mirrors Tuesday but Sunday scaling is predeclared from Sunday geometry/path speed. D selects only EMA20 overextension threshold; V is report-only. Entire historical Sunday sample has prior research exposure, so not untouched OOS.
