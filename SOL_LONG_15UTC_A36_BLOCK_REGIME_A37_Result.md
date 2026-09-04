# SOL LONG 15:00 UTC A36 Block / Regime Anatomy — A37 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A37 is forensic only. All studied features are observable by the A36 recovery entry.

## Strong replicated pre-entry separation

| Feature | Stress-win median | Stress-fail median | Dev gap | Robust effect | External gap | RefVal gap | Support same dir |
|---|---:|---:|---:|---:|---:|---:|---:|
| parent_mae_R | 0.130 | 0.160 | -0.031 | 0.71 | -0.056 | -0.047 | 5/4 |
| running_mfe_R_to_confirm | 0.305 | 0.252 | 0.053 | 0.66 | 0.098 | 0.045 | 5/4 |

## Development block anatomy

| Block | N | Raw WR | Stress WR | Raw PF | Stress PF | Raw net | Stress net | Rescue | Median parent_mae_R | Median running_mfe_R_to_confirm |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 80.0% | 80.0% | 1.04 | 0.86 | $0.26 | $-0.99 | 80.0% | 0.142 | 0.353 |
| 2 | 5 | 20.0% | 20.0% | 0.35 | 0.27 | $-4.52 | $-5.77 | 20.0% | 0.160 | 0.272 |
| 3 | 1 | 0.0% | 0.0% | 0.00 | 0.00 | $-1.81 | $-2.06 | 0.0% | 0.199 | 0.272 |
| 4 | 3 | 33.3% | 33.3% | 0.13 | 0.09 | $-5.95 | $-6.70 | 33.3% | 0.204 | 0.185 |
| 5 | 6 | 83.3% | 66.7% | 6.19 | 4.99 | $13.38 | $11.88 | 66.7% | 0.164 | 0.314 |
| 6 | 7 | 57.1% | 57.1% | 2.28 | 1.79 | $6.09 | $4.34 | 57.1% | 0.128 | 0.205 |

## Decision

Strong replicated causal features: **2**.

**Status: SOL_LONG_15UTC_A36_BLOCK_REGIME_A37_SUPPORTED_FOR_A38**

If supported, A38 may test at most three Development-derived guards from these features. No threshold grid and no OOS retuning.

Research only. Live Baba Bot remains unchanged.
