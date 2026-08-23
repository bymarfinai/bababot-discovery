# B27BP — BTC 24H BULL→SIDEWAYS 5m Pre-Second-Retest Anatomy — Result

**Audit status: PASS.** Regime microstructure only; no entry price, trade direction, stop, target, fee, WR, PF, PnL, or live change was used.

Parent identity reproduced exactly: **532 BULL-origin episodes = 281 RESUME + 251 TRANSITION; pooled OOS 313.**

The frozen swing low is known at the last completed BULL state. 5m monitoring starts immediately then, so Retest #1 / leave / Retest #2 chronology is causal.

## Pooled OOS

- Frozen boundary available: **313/313 = 100.0%**.
- Clean Retest#1 -> completed leave windows: **42 / 313 = 13.4%**.
- Retest #2 arrivals after a clean leave: **32 / 42 = 76.2%**.
- Positive-duration pre-R2 windows: **27 / 32** R2-arrival cases.
- Median eligible-start -> R2 arrival: **45.0 min** (9.0 completed 5m bars before R2); P25 **5.0 min**, P75 **106.2 min**.

### Exact 5m path status

| Status | N | Share | RESUME | TRANSITION | RESUME rate |
|---|---:|---:|---:|---:|---:|
| NO_R1 | 182 | 58.1% | 114 | 68 | 62.6% |
| BREAK_ON_FIRST_ARRIVAL | 80 | 25.6% | 35 | 45 | 43.8% |
| BREAK_DURING_R1 | 9 | 2.9% | 5 | 4 | 55.6% |
| R1_NO_CAUSAL_LEAVE | 0 | 0.0% | 0 | 0 | - |
| CLEAN_WINDOW_NO_R2 | 10 | 3.2% | 8 | 2 | 80.0% |
| R2_DEFENDED | 16 | 5.1% | 8 | 8 | 50.0% |
| R2_BREAK | 16 | 5.1% | 6 | 10 | 37.5% |

### Retest #2 outcome readout

- BULL-origin baseline RESUME rate: **56.2%**.
- `R2_DEFENDED`: N **16**, RESUME **50.0%**, TRANSITION **50.0%**.
- `R2_BREAK`: N **16**, RESUME **37.5%**, TRANSITION **62.5%**.
- Defended-minus-break RESUME separation: **+12.5pp**.

## OOS partition stability

| Partition | R2 defended N | RESUME | R2 break N | RESUME | Defended > break? |
|---|---:|---:|---:|---:|---|
| external | 13 | 53.8% | 11 | 27.3% | YES |
| reference_validation | 3 | 33.3% | 5 | 60.0% | NO |

## Frozen support gate

- Exact source/detector/parent identity: **PASS**.
- Boundary available >=95% pooled OOS: **PASS**.
- Clean inter-retest window N >=40 pooled OOS: **PASS**.
- R2_DEFENDED and R2_BREAK N >=20 pooled OOS: **FAIL**.
- Pooled OOS RESUME(R2_DEFENDED) > RESUME(R2_BREAK): **PASS**.
- Same positive sign in external and validation with >=5/cell: **FAIL**.
- Retest #2 strictly after completed causal leave / event exclusivity: **PASS**.

**Frozen verdict: `B27BP_BULL_5M_TWO_RETEST_GEOMETRY_NOT_SUPPORTED`.**

Interpretation boundary: a supported result means only that the exact 5m two-retest geometry carries stable continuation-vs-breakdown information. It does not yet promote F15/F85 or any entry.

Research only. Live BBC unchanged.
