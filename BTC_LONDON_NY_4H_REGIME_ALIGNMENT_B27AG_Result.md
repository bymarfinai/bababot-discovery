# B27AG — BTC London -> New York 4H HH/HL Regime Alignment Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Existing 4H SwingRegime semantics/defaults were reproduced, only fully completed 4H bars were available to each K1 signal, frozen F85/F15 cohorts reproduced, and existing fixed-E20 totals reproduced before regime attribution.

## Pooled-major structural funnel by pre-signal 4H state

| Side | 4H state | Alignment | K1 N | Target break | Clean | Fills | H2/fill | Accept/H2 | E20/H2 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| LONG | BULL | ALIGNED | 185 | 82.2% | 61.6% | 68 | 80.9% | 90.9% | 85.5% |
| LONG | BEAR | COUNTER | 113 | 76.1% | 72.6% | 55 | 80.0% | 95.5% | 84.1% |
| LONG | SIDEWAYS | SIDEWAYS | 49 | 83.7% | 79.6% | 26 | 84.6% | 100.0% | 90.9% |
| SHORT | BULL | COUNTER | 170 | 74.7% | 65.9% | 71 | 69.0% | 85.7% | 79.6% |
| SHORT | BEAR | ALIGNED | 140 | 74.3% | 71.4% | 59 | 76.3% | 86.7% | 84.4% |
| SHORT | SIDEWAYS | SIDEWAYS | 68 | 79.4% | 73.5% | 33 | 78.8% | 92.3% | 80.8% |

## Confirmed-entry economics by pre-signal 4H state

| Side | Rule | State | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG | EARLY_RECLAIM | BULL | 55 | 70.9% | 1.66 | $+0.84 | $+46.12 | 69.1% | 1.98 | $+1.25 | $+68.55 |
| LONG | EARLY_RECLAIM | BEAR | 41 | 63.4% | 1.04 | $+0.06 | $+2.63 | 51.2% | 0.99 | $-0.02 | $-0.67 |
| LONG | EARLY_RECLAIM | SIDEWAYS | 22 | 86.4% | 2.33 | $+1.26 | $+27.77 | 86.4% | 2.70 | $+1.61 | $+35.42 |
| SHORT | EARLY_REJECT | BULL | 52 | 51.9% | 0.56 | $-0.75 | $-38.75 | 46.2% | 0.78 | $-0.38 | $-19.76 |
| SHORT | EARLY_REJECT | BEAR | 41 | 58.5% | 0.90 | $-0.17 | $-6.99 | 51.2% | 0.66 | $-0.63 | $-25.69 |
| SHORT | EARLY_REJECT | SIDEWAYS | 27 | 74.1% | 2.16 | $+1.41 | $+38.06 | 66.7% | 2.25 | $+1.58 | $+42.64 |

## Combined confirmed-entry alignment

| Alignment | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALIGNED | 96 | 65.6% | 1.28 | $+0.41 | $+39.12 | 61.5% | 1.29 | $+0.45 | $+42.86 |
| COUNTER | 93 | 57.0% | 0.77 | $-0.39 | $-36.12 | 48.4% | 0.87 | $-0.22 | $-20.43 |
| SIDEWAYS | 49 | 79.6% | 2.23 | $+1.34 | $+65.82 | 75.5% | 2.42 | $+1.59 | $+78.06 |

## Frozen hypothesis readout

- SHORT H2: BEAR 76.3% vs BULL 69.0% -> PASS
- SHORT E20/H2: BEAR 84.4% vs BULL 79.6% -> PASS
- LONG H2: BULL 80.9% vs BEAR 80.0% -> PASS
- LONG E20/H2: BULL 85.5% vs BEAR 84.1% -> PASS
- Confirmed fixed expectancy: ALIGNED $+0.41 (N=96) vs COUNTER $-0.39 (N=93) -> PASS

**Overall: B27AG_REGIME_HYPOTHESIS_DIRECTIONALLY_SUPPORTED.**

This audit attributes existing trades to a pre-existing causal 4H state. It does not authorize a new live regime filter. Small regime cells remain a limitation.

Research only; live BBC unchanged.
