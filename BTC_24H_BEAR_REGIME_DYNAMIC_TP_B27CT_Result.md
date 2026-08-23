# B27CT — BTC 24H BEAR Regime-Filter + Dynamic Clock-TP Economics — Result

5m rows: **698,112**; coverage **100.0000%**.

**Audit status: PASS.** Exact B27CS all-regime executable fills reproduced: external 183 / development 297 / validation 172 / pooled major 652. Causal 4H regime provenance verified before each obs_start.

Frozen filter: **ALLOW BEAR + SIDEWAYS; BLOCK BULL**. Entry remains F05. Clock TP map remains B27CR. Dynamic variant turns the final clock target into a next-bar profit ceiling and ratchets it down only with strict causal 3-bar pivot highs.

Economics: $500 notional and $0.40 round-trip fee. External/reference_validation are reused-data confirmation, not untouched OOS.

## Six clocks first — filtered DYNAMIC

| UTC / WIB | TP | N | WR | PF | Exp/trade | Net | Avg win | Avg loss | Max DD | Loss streak | Target reach | Target-floor | Pivot exit | High SL | Time |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 00-04 / 07-11 | T5 | 53 | 54.7% | 0.55 | $-0.95 | $-50.20 | $+2.14 | $-4.68 | $55.87 | 4 | 40 | 33 | 7 | 8 | 5 |
| 04-08 / 11-15 | T15 | 59 | 62.7% | 1.86 | $+0.93 | $+55.12 | $+3.23 | $-2.93 | $30.44 | 4 | 21 | 17 | 3 | 3 | 7 |
| 08-12 / 15-19 | T15 | 60 | 58.3% | 0.77 | $-0.27 | $-16.33 | $+1.52 | $-2.78 | $32.46 | 3 | 29 | 22 | 7 | 9 | 1 |
| 12-16 / 19-23 | T10 | 85 | 63.5% | 0.84 | $-0.16 | $-13.85 | $+1.39 | $-2.86 | $36.15 | 5 | 55 | 50 | 5 | 11 | 3 |
| 16-20 / 23-03 | T10 | 66 | 65.2% | 0.57 | $-0.70 | $-45.98 | $+1.41 | $-4.63 | $50.57 | 3 | 31 | 26 | 4 | 6 | 9 |
| 20-00 / 03-07 | T15 | 57 | 56.1% | 0.74 | $-0.24 | $-13.94 | $+1.25 | $-2.16 | $29.54 | 8 | 26 | 23 | 3 | 6 | 9 |

## Major partitions — filtered FIXED vs DYNAMIC

| Partition | Variant | N | WR | PF | Exp/trade | Net | Avg win | Avg loss | Max DD | Loss streak | Target reach | High SL | Time |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | FIXED_CLOCK_TP | 94 | 73.4% | 0.91 | $-0.18 | $-16.58 | $+2.54 | $-7.67 | $59.37 | 6 | 51 | 10 | 8 |
| external | DYNAMIC_CLOCK_TP | 94 | 69.1% | 1.08 | $+0.17 | $+15.52 | $+3.22 | $-6.69 | $75.00 | 6 | 51 | 10 | 10 |
| development | FIXED_CLOCK_TP | 196 | 64.8% | 0.70 | $-0.29 | $-57.39 | $+1.07 | $-2.81 | $77.29 | 6 | 102 | 21 | 16 |
| development | DYNAMIC_CLOCK_TP | 196 | 58.2% | 0.69 | $-0.31 | $-61.11 | $+1.19 | $-2.41 | $77.56 | 6 | 102 | 21 | 16 |
| reference_validation | FIXED_CLOCK_TP | 90 | 65.6% | 0.69 | $-0.32 | $-29.25 | $+1.13 | $-3.09 | $53.19 | 4 | 49 | 12 | 8 |
| reference_validation | DYNAMIC_CLOCK_TP | 90 | 56.7% | 0.62 | $-0.44 | $-39.58 | $+1.27 | $-2.68 | $66.75 | 5 | 49 | 12 | 8 |
| POOLED_MAJOR | FIXED_CLOCK_TP | 380 | 67.1% | 0.79 | $-0.27 | $-103.22 | $+1.48 | $-3.85 | $122.91 | 6 | 202 | 43 | 32 |
| POOLED_MAJOR | DYNAMIC_CLOCK_TP | 380 | 60.5% | 0.83 | $-0.22 | $-85.17 | $+1.78 | $-3.30 | $119.73 | 6 | 202 | 43 | 34 |

## Filter effect — fixed clock TP

| Population | N | WR | PF | Exp/trade | Net |
|---|---:|---:|---:|---:|---:|
| ALL regimes | 652 | 66.6% | 0.67 | $-0.43 | $-278.39 |
| BEAR + SIDEWAYS allowed | 380 | 67.1% | 0.79 | $-0.27 | $-103.22 |
| BULL blocked cohort only | 272 | 65.8% | 0.50 | $-0.64 | $-175.17 |

## Dynamic effect on the same filtered cohort

| Metric | FIXED | DYNAMIC |
|---|---:|---:|
| Trades | 380 | 380 |
| WR | 67.1% | **60.5%** |
| PF | 0.79 | **0.83** |
| Expectancy/trade | $-0.27 | **$-0.22** |
| Total net | $-103.22 | **$-85.17** |
| Avg win | $+1.48 | **$+1.78** |
| Avg loss | $-3.85 | **$-3.30** |
| Max DD | $122.91 | **$119.73** |

## Filtered regime components — DYNAMIC

| Regime | N | WR | PF | Exp/trade | Net | Target reach | High SL |
|---|---:|---:|---:|---:|---:|---:|---:|
| BEAR | 284 | 60.2% | 0.80 | $-0.27 | $-76.52 | 154 | 31 |
| SIDEWAYS | 96 | 61.5% | 0.93 | $-0.09 | $-8.66 | 48 | 12 |

## Per 100 filtered DYNAMIC trades

- Net winners: **60.5**.
- Full structural High losses: **11.3**.
- Final clock target reached: **53.2**.
- Target-floor exits: **45.0**.
- Structural pivot exits: **7.6**.
- Time exits: **8.9**.

HIGH_QUALITY_70: **FAIL**.

**Frozen verdict: `B27CT_BEAR_FILTER_DYNAMIC_NOT_SUPPORTED`.**

No post-hoc filter, target, pivot, SL, clock, or horizon changes were made. Live BBC unchanged.
