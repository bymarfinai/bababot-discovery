# ETH B27DX — S8L Loss Anatomy — Result

ETH raw 5m coverage: **100.0000%**.

Frozen portfolio: **R300/X360 · F75/E25/F20 · 05:00/09:00/10:00/16:00 UTC · S4 global one-position lock**.

- Candidate/parity/causal audit: **PASS**.
- Accepted trades: **478**; wins **300**; losses **178**; loss rate **37.2%**.

## Where losses concentrate

| Clock | N | Losses | Loss rate | Share of all losses | Mean loss PnL |
|---:|---:|---:|---:|---:|---:|
| 05:00 | 101 | 38 | 37.6% | 21.3% | -3.75 |
| 09:00 | 90 | 34 | 37.8% | 19.1% | -5.82 |
| 10:00 | 164 | 55 | 33.5% | 30.9% | -5.04 |
| 16:00 | 123 | 51 | 41.5% | 28.7% | -5.85 |

## Causal pre-entry associations with loss

Positive continuous effect means the feature is **higher on losses**; negative means **lower on losses**. No cutoff was optimized.

**No continuous feature met the frozen three-partition directional-replication criterion.**

### Strongest pooled continuous signals (diagnostic; not automatically replicated)

| Feature | Effect | Loss median | Win median | Replicated |
|---|---:|---:|---:|---|
| post_leave_to_fill_frac | 0.150 | 0.014 | 0.000 | NO |
| k1_to_fill_frac | 0.131 | 0.049 | 0.042 | NO |
| extreme_spacing_frac | 0.109 | 0.533 | 0.475 | NO |
| range_completion_frac | 0.108 | 0.817 | 0.733 | NO |
| pre24_vol | -0.090 | 0.002 | 0.002 | NO |
| pre4_return | -0.073 | 0.000 | 0.001 | NO |
| pre24_range_pct | -0.058 | 0.050 | 0.055 | NO |
| leave_drop_from_H_R | -0.048 | 0.162 | 0.177 | NO |

## Natural binary anatomy

**No natural binary feature met the frozen three-partition replication criterion.**

## Ex-post loss path — diagnostic only, never an entry filter

| Exit reason | Losses | Share | Median hold min | Median MFE/R | Median MAE/R | Median target progress | Near-target >=80% |
|---|---:|---:|---:|---:|---:|---:|---:|
| CLOSE_INVALIDATION | 102 | 57.3% | 107.5 | 0.144 | 0.695 | 28.8% | 5.9% |
| TIME_EXIT | 76 | 42.7% | 250.0 | 0.156 | 0.365 | 31.3% | 6.6% |

## Decision

**Status: ETH_S8L_LOSS_ANATOMY_COMPLETED_NO_REPLICATED_ASSOCIATION**

- S8L does not create or optimize a new trading rule.
- Replicated pre-entry associations, if any, are hypotheses for a separately preregistered validation test.
- MFE/MAE/exit-path observations are ex-post explanations only and cannot be used as causal entry information.
