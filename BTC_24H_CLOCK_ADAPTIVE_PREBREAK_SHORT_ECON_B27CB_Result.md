# B27CB — BTC 24H Clock-Adaptive Pre-Break SHORT Economic Backtest — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Exact B27CA clock-selected entries were reused. All variants have nominal RR >=1:1. Same-fill-bar and same-bar TP/STOP ambiguity is resolved conservatively in favor of STOP.

Illustrative economics: **$500 notional/trade, $0.40 round-trip fee, no extra slippage**.

Frozen B27CA clock entries: **00-04 F05 / 04-08 F05 / 08-12 F10 / 12-16 F05 / 16-20 F05 / 20-00 F05**.

## Major-partition economics

| Variant | RR | Partition | N | WR | PF | Exp/trade | Total net | TP | STOP | TIME |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S1_T1 | 1.00 | external | 250 | 3.6% | 0.03 | $-1.03 | $-257.24 | 9 | 241 | 0 |
| S1_T1 | 1.00 | development | 380 | 5.3% | 0.04 | $-0.77 | $-292.80 | 32 | 347 | 1 |
| S1_T1 | 1.00 | reference_validation | 177 | 5.1% | 0.03 | $-0.68 | $-119.90 | 20 | 155 | 2 |
| S1_T1_5 | 1.50 | external | 250 | 2.8% | 0.04 | $-1.03 | $-258.33 | 7 | 243 | 0 |
| S1_T1_5 | 1.50 | development | 380 | 4.7% | 0.06 | $-0.78 | $-296.59 | 24 | 355 | 1 |
| S1_T1_5 | 1.50 | reference_validation | 177 | 7.3% | 0.04 | $-0.68 | $-120.14 | 17 | 157 | 3 |
| S1_T2 | 2.00 | external | 250 | 2.4% | 0.04 | $-1.04 | $-259.78 | 6 | 244 | 0 |
| S1_T2 | 2.00 | development | 380 | 5.5% | 0.09 | $-0.76 | $-288.14 | 23 | 356 | 1 |
| S1_T2 | 2.00 | reference_validation | 177 | 6.8% | 0.05 | $-0.68 | $-121.24 | 13 | 161 | 3 |
| S1_5_T1_5 | 1.00 | external | 250 | 7.6% | 0.07 | $-1.24 | $-309.81 | 19 | 231 | 0 |
| S1_5_T1_5 | 1.00 | development | 380 | 8.4% | 0.06 | $-0.93 | $-354.53 | 45 | 329 | 6 |
| S1_5_T1_5 | 1.00 | reference_validation | 177 | 14.1% | 0.07 | $-0.72 | $-127.93 | 36 | 138 | 3 |
| S1_5_T2 | 1.33 | external | 250 | 7.2% | 0.09 | $-1.22 | $-304.64 | 18 | 232 | 0 |
| S1_5_T2 | 1.33 | development | 380 | 9.5% | 0.09 | $-0.91 | $-347.15 | 41 | 331 | 8 |
| S1_5_T2 | 1.33 | reference_validation | 177 | 15.3% | 0.10 | $-0.71 | $-126.33 | 32 | 142 | 3 |
| S2_T2 | 1.00 | external | 250 | 11.6% | 0.11 | $-1.39 | $-348.15 | 29 | 220 | 1 |
| S2_T2 | 1.00 | development | 380 | 20.0% | 0.15 | $-0.87 | $-332.01 | 84 | 280 | 16 |
| S2_T2 | 1.00 | reference_validation | 177 | 20.3% | 0.12 | $-0.76 | $-134.48 | 44 | 128 | 5 |

## Pooled OOS

| Variant | RR | N | WR | PF | Exp/trade | Total net |
|---|---:|---:|---:|---:|---:|---:|
| S1_T1 | 1.00 | 427 | 4.2% | 0.03 | $-0.88 | $-377.14 |
| S1_T1_5 | 1.50 | 427 | 4.7% | 0.04 | $-0.89 | $-378.48 |
| S1_T2 | 2.00 | 427 | 4.2% | 0.04 | $-0.89 | $-381.02 |
| S1_5_T1_5 | 1.00 | 427 | 10.3% | 0.07 | $-1.03 | $-437.74 |
| S1_5_T2 | 1.33 | 427 | 10.5% | 0.09 | $-1.01 | $-430.97 |
| S2_T2 | 1.00 | 427 | 15.2% | 0.11 | $-1.13 | $-482.63 |

## Clock diagnostics — S2_T2

If no variant passes the frozen gate, this table is diagnostic only and does not select/promote the variant.

| UTC block | Entry | OOS N | OOS WR | OOS PF | OOS Exp | Major N | Major WR | Major PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 00-04 | F05 | 55 | 10.9% | 0.05 | $-1.14 | 109 | 15.6% | 0.08 |
| 04-08 | F05 | 76 | 13.2% | 0.04 | $-1.11 | 128 | 16.4% | 0.05 |
| 08-12 | F10 | 101 | 31.7% | 0.27 | $-1.03 | 186 | 30.1% | 0.25 |
| 12-16 | F05 | 73 | 8.2% | 0.06 | $-1.12 | 140 | 10.7% | 0.09 |
| 16-20 | F05 | 67 | 13.4% | 0.10 | $-1.14 | 146 | 13.0% | 0.11 |
| 20-00 | F05 | 55 | 3.6% | 0.02 | $-1.34 | 98 | 13.3% | 0.10 |

## Frozen gate

- S1_T1: ROBUST_PASS **FAIL**; HIGH_QUALITY_70 **FAIL**; min major PF 0.03; pooled-OOS expectancy $-0.88.
- S1_T1_5: ROBUST_PASS **FAIL**; HIGH_QUALITY_70 **FAIL**; min major PF 0.04; pooled-OOS expectancy $-0.89.
- S1_T2: ROBUST_PASS **FAIL**; HIGH_QUALITY_70 **FAIL**; min major PF 0.04; pooled-OOS expectancy $-0.89.
- S1_5_T1_5: ROBUST_PASS **FAIL**; HIGH_QUALITY_70 **FAIL**; min major PF 0.06; pooled-OOS expectancy $-1.03.
- S1_5_T2: ROBUST_PASS **FAIL**; HIGH_QUALITY_70 **FAIL**; min major PF 0.09; pooled-OOS expectancy $-1.01.
- S2_T2: ROBUST_PASS **FAIL**; HIGH_QUALITY_70 **FAIL**; min major PF 0.11; pooled-OOS expectancy $-1.13.

**Frozen verdict: `B27CB_CLOCK_ADAPTIVE_ECON_NOT_SUPPORTED`.**

No economic geometry passed. Do not rescue a clock, stop, or target post hoc inside B27CB. Research only; live BBC unchanged.
