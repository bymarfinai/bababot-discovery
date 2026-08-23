# B27CD — BTC 24H Clock-Adaptive R4-Risk SHORT Economics — Result

5m rows: **698,112**; coverage **100.0000%**.

**Audit status: PASS.** Exact B27CC/B27CA adaptive filled-entry identity reproduced: external 250 / development 380 / validation 177. One anatomy-derived 1:1 rule only; no stop/target sweep.

Illustrative economics: **$500 notional/trade, $0.40 round-trip fee, no extra slippage**. Same-bar ambiguity is conservative: STOP wins; fill-bar TP is not credited.

## Development-only frozen R4 stops

| UTC block | Entry | Dev winner N | Dev MAE P75 %R4 | Frozen stop | Target | RR |
|---|---|---:|---:|---:|---:|---:|
| 00-04 | F05 | 37 | 17.3% | 20.0% R4 | 20.0% R4 | 1.00 |
| 04-08 | F05 | 35 | 20.2% | 25.0% R4 | 25.0% R4 | 1.00 |
| 08-12 | F10 | 50 | 26.3% | 30.0% R4 | 30.0% R4 | 1.00 |
| 12-16 | F05 | 43 | 27.8% | 30.0% R4 | 30.0% R4 | 1.00 |
| 16-20 | F05 | 59 | 20.2% | 25.0% R4 | 25.0% R4 | 1.00 |
| 20-00 | F05 | 29 | 13.0% | 15.0% R4 | 15.0% R4 | 1.00 |

## Major partitions

| Partition | N | WR | PF | Exp/trade | Total net | TP | STOP | TIME |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 250 | 37.6% | 0.48 | $-1.00 | $-251.01 | 89 | 141 | 20 |
| development | 380 | 35.8% | 0.48 | $-0.68 | $-259.15 | 130 | 193 | 57 |
| reference_validation | 177 | 37.9% | 0.41 | $-0.65 | $-115.08 | 64 | 91 | 22 |

## Pooled

| Scope | N | WR | PF | Exp/trade | Total net |
|---|---:|---:|---:|---:|---:|
| POOLED_OOS | 427 | 37.7% | 0.46 | $-0.86 | $-366.09 |
| POOLED_MAJOR | 807 | 36.8% | 0.47 | $-0.77 | $-625.24 |

## Clock diagnostics

| UTC block | Stop %R4 | OOS N | OOS WR | OOS PF | OOS Exp | OOS Net | Major N | Major WR | Major PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 00-04 | 20.0% | 55 | 36.4% | 0.43 | $-0.80 | $-43.86 | 109 | 34.9% | 0.43 |
| 04-08 | 25.0% | 76 | 42.1% | 0.55 | $-0.64 | $-48.83 | 128 | 37.5% | 0.57 |
| 08-12 | 30.0% | 101 | 42.6% | 0.54 | $-0.70 | $-70.79 | 186 | 43.0% | 0.57 |
| 12-16 | 30.0% | 73 | 45.2% | 0.60 | $-0.66 | $-47.90 | 140 | 36.4% | 0.42 |
| 16-20 | 25.0% | 67 | 31.3% | 0.38 | $-1.23 | $-82.48 | 146 | 35.6% | 0.48 |
| 20-00 | 15.0% | 55 | 21.8% | 0.15 | $-1.31 | $-72.23 | 98 | 28.6% | 0.25 |

## Frozen gate

- N gate: **PASS**.
- Positive expectancy in all major partitions: **FAIL**.
- PF >=1.20 in all major partitions: **FAIL**.
- WR >=50% in all major partitions: **FAIL**.
- Pooled-OOS PF >=1.20 and expectancy >0: **FAIL**.
- HIGH_QUALITY_70: **FAIL**.

**Frozen verdict: `B27CD_R4_RISK_ECON_NOT_SUPPORTED`.**

Research only. No live BBC change. No failed clock may be removed post hoc inside B27CD.
