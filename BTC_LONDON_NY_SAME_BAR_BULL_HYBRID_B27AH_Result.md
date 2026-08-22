# B27AH — SAME_BAR_REJECTION + 4H BULL Hybrid Attribution — Result

**Audit status: PASS.** Existing B27AC SAME_BAR pooled-major cohort/economics and B27AG causal pre-signal regime labels reproduce before attribution.

## Pooled major: same trades, split only by pre-signal 4H state

| 4H state | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 68 | 73.5% | 1.70 | $+0.91 | $+61.80 | 69.1% | 2.03 | $+1.34 | $+91.31 |
| BULL | 37 | 70.3% | 1.63 | $+0.84 | $+30.92 | 67.6% | 2.14 | $+1.52 | $+56.35 |
| BEAR | 19 | 68.4% | 1.37 | $+0.53 | $+10.05 | 57.9% | 1.71 | $+1.02 | $+19.41 |
| SIDEWAYS | 12 | 91.7% | 2.68 | $+1.74 | $+20.84 | 91.7% | 2.25 | $+1.30 | $+15.56 |

## 4H BULL only by major partition

| Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 14 | 71.4% | 1.31 | $+0.43 | $+6.06 | 64.3% | 0.96 | $-0.06 | $-0.88 |
| development | 16 | 62.5% | 1.62 | $+0.99 | $+15.90 | 62.5% | 2.89 | $+3.03 | $+48.45 |
| reference_validation | 7 | 85.7% | 3.86 | $+1.28 | $+8.96 | 85.7% | 3.80 | $+1.25 | $+8.77 |

## Frozen readout

- Original SAME_BAR all-regime hybrid: N=68, WR=69.1%, PF=2.03, exp=$+1.34, total=$+91.31.
- SAME_BAR + 4H BULL hybrid: N=37, WR=67.6%, PF=2.14, exp=$+1.52, total=$+56.35.
- SAME_BAR + 4H BEAR hybrid: N=19, WR=57.9%, PF=1.71, exp=$+1.02, total=$+19.41.
- SAME_BAR + 4H SIDEWAYS hybrid: N=12, WR=91.7%, PF=2.25, exp=$+1.30, total=$+15.56.

**Overall: B27AH_BULL_CONCENTRATION_IMPROVES_HYBRID.**

This remains a post-hoc attribution of an adaptively observed SAME_BAR subset, not an independent OOS promotion. Research only; live BBC unchanged.
