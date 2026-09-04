# SOL LONG 15:00 UTC A36 Block / Regime Anatomy — A37B Corrected Result

A37B corrects only the topology support counter. Exact A37 trade ledger and medians are reused.

## Strong replicated pre-entry separation

| Feature | Stress-win median | Stress-fail median | Dev gap | Robust effect | External gap | RefVal gap | Support same dir |
|---|---:|---:|---:|---:|---:|---:|---:|
| parent_mae_R | 0.130 | 0.160 | -0.031 | 0.71 | -0.056 | -0.047 | 3/4 |
| running_mfe_R_to_confirm | 0.305 | 0.252 | 0.053 | 0.66 | 0.098 | 0.045 | 3/4 |

## Decision

Corrected strong replicated features: **2**.

**Status: SOL_LONG_15UTC_A36_BLOCK_REGIME_A37B_SUPPORTED_FOR_A38**

A38 is authorized only if this corrected report retains at least two strong replicated features. No threshold grid or OOS retuning.

