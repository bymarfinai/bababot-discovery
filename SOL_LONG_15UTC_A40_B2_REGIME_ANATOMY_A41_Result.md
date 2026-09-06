# SOL LONG 15:00 UTC A40 B2 Regime Anatomy — A41 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A41 is forensic only. E20/E10/E40 geometry is frozen; all features are observable by the E20 entry.

## Strong replicated B2 separators

| Feature | Stress-win median | Stress-fail median | Dev gap | Effect | B2 median | B1/B5/B6 median | External gap | RefVal gap | Support |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| parent_mae_R | 0.130 | 0.160 | -0.031 | 0.87 | 0.160 | 0.130 | -0.086 | -0.042 | 3/4 |
| preentry_30m_return_R | 0.270 | 0.169 | 0.101 | 0.85 | 0.169 | 0.249 | 0.033 | 0.092 | 3/4 |
| preentry_30m_range_R | 0.439 | 0.359 | 0.079 | 0.58 | 0.359 | 0.414 | 0.013 | 0.044 | 3/4 |
| running_mfe_R_to_confirm | 0.309 | 0.272 | 0.037 | 0.51 | 0.272 | 0.308 | 0.089 | 0.040 | 3/4 |

## Development blocks

| Block | N | WR | Stress WR | PF | Stress PF | Net | Stress Net |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 80.0% | 80.0% | 1.80 | 1.55 | $4.41 | $3.16 |
| 2 | 5 | 20.0% | 20.0% | 0.24 | 0.18 | $-5.99 | $-7.24 |
| 3 | 1 | 0.0% | 0.0% | 0.00 | 0.00 | $-2.55 | $-2.80 |
| 4 | 1 | 100.0% | 100.0% | inf | inf | $0.71 | $0.46 |
| 5 | 5 | 80.0% | 80.0% | 12.88 | 9.99 | $14.35 | $13.10 |
| 6 | 6 | 66.7% | 66.7% | 2.26 | 1.86 | $6.12 | $4.62 |

## Decision

Strong B2 separators: **4**.

**Status: SOL_LONG_15UTC_A40_B2_REGIME_A41_SUPPORTED_FOR_A42**

If supported, A42 may test at most three Development-midpoint guards from these exact features. No E20/E10 change and no OOS retuning.

Research only. Live Baba Bot remains unchanged.
