# ETH LONG B27AG-Adapt — 4H HH/HL Regime Alignment Audit — Result

ETHUSDT 5m rows: **698,112**; coverage: **100.0000%**; complete 4H bars: **14,544**.

The repository SwingRegime defaults are reproduced causally. Regime is attached at K1 signal time using only the latest completed 4H bar. No trade is filtered.

| Partition | Regime | K1 N | Target break | F75 fills | H2 | H2 rate | E10/H2 | ER N | Fixed WR | Fixed PF | Fixed exp | Fixed net | Hybrid PF | Hybrid exp | Hybrid net |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | BULL | 69 | 84.1% | 30 | 21 | 70.0% | 90.5% | 28 | 67.9% | 0.76 | $-0.78 | $-21.83 | 0.93 | $-0.23 | $-6.38 |
| external | BEAR | 23 | 82.6% | 6 | 5 | 83.3% | 100.0% | 6 | 83.3% | 6.77 | $2.47 | $14.82 | 6.64 | $2.41 | $14.48 |
| external | SIDEWAYS | 28 | 92.9% | 6 | 5 | 83.3% | 100.0% | 6 | 83.3% | 15.83 | $4.50 | $27.03 | 13.91 | $3.92 | $23.52 |
| development | BULL | 83 | 75.9% | 38 | 26 | 68.4% | 96.2% | 33 | 69.7% | 0.82 | $-0.50 | $-16.39 | 0.90 | $-0.28 | $-9.17 |
| development | BEAR | 74 | 82.4% | 24 | 20 | 83.3% | 95.0% | 18 | 83.3% | 3.41 | $1.54 | $27.75 | 2.93 | $1.25 | $22.43 |
| development | SIDEWAYS | 16 | 81.2% | 3 | 2 | 66.7% | 100.0% | 3 | 66.7% | 0.41 | $-1.12 | $-3.36 | 0.42 | $-1.10 | $-3.30 |
| reference_validation | BULL | 44 | 84.1% | 17 | 12 | 70.6% | 100.0% | 14 | 71.4% | 0.80 | $-0.49 | $-6.88 | 0.70 | $-0.75 | $-10.54 |
| reference_validation | BEAR | 31 | 80.6% | 8 | 6 | 75.0% | 100.0% | 8 | 75.0% | 1.73 | $1.60 | $12.83 | 1.68 | $1.49 | $11.91 |
| reference_validation | SIDEWAYS | 10 | 70.0% | 6 | 4 | 66.7% | 100.0% | 6 | 66.7% | 0.81 | $-0.70 | $-4.21 | 0.66 | $-1.25 | $-7.49 |
| august | BULL | 2 | 100.0% | 1 | 1 | 100.0% | 100.0% | 1 | 100.0% | inf | $4.66 | $4.66 | inf | $4.66 | $4.66 |
| august | BEAR | 1 | 0.0% | 1 | 0 | 0.0% | - | 1 | 0.0% | 0.00 | $-6.13 | $-6.13 | 0.00 | $-6.13 | $-6.13 |
| august | SIDEWAYS | 0 | - | 0 | 0 | - | - | 0 | - | - | $- | $0.00 | - | $- | $0.00 |
| POOLED_MAJOR | BULL | 196 | 80.6% | 85 | 59 | 69.4% | 94.9% | 75 | 69.3% | 0.79 | $-0.60 | $-45.10 | 0.88 | $-0.35 | $-26.09 |
| POOLED_MAJOR | BEAR | 128 | 82.0% | 38 | 31 | 81.6% | 96.8% | 32 | 81.2% | 2.75 | $1.73 | $55.40 | 2.54 | $1.53 | $48.82 |
| POOLED_MAJOR | SIDEWAYS | 54 | 85.2% | 15 | 11 | 73.3% | 100.0% | 15 | 73.3% | 1.66 | $1.30 | $19.46 | 1.43 | $0.85 | $12.73 |

## Frozen directional-support readout

- BULL vs BEAR F75 H2 rate: 69.4% vs 81.6%.
- BULL vs BEAR E10 reach given H2: 94.9% vs 96.8%.
- BULL vs BEAR EARLY_RECLAIM fixed expectancy: $-0.60 vs $1.73.

**Status: ETH_LONG_B27AG_ADAPT_REGIME_ALIGNMENT_NOT_DIRECTIONALLY_SUPPORTED**

Attribution only; this does not authorize a regime filter. Research only; no live changes.
