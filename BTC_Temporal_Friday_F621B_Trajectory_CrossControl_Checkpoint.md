# Friday F6.21b — Trajectory Cross-Control Check

**Status: COMPLETE — FORENSIC ONLY; NO EXIT RULE TUNED/PROMOTED.**
**Live BBC untouched; frozen stack unchanged.**

This check guards against selection bias from using F6.20 false-positive winners as the primary control. A separator is cross-stable only if it passes the same frozen full/D/V stability screen against BOTH false-positive winners and all broad eligible winners, with the same loss direction.

## Cross-stable separators: **0**
- none

## Focus check
- 65m taker_last2_mean: FP direction lower_loss, AUC 0.292 D/V 0.309/0.267; broad direction lower_loss, AUC 0.381 D/V 0.384/0.349; cross-stable False
- 65m longest_below_ema7: FP direction higher_loss, AUC 0.613 D/V 0.574/0.733; broad direction higher_loss, AUC 0.850 D/V 0.816/0.929; cross-stable False
- 35m progress_last3_slope: FP direction lower_loss, AUC 0.435 D/V 0.593/0.000; broad direction lower_loss, AUC 0.268 D/V 0.315/0.063; cross-stable False
- 65m bars_since_above_ema7: FP direction higher_loss, AUC 0.577 D/V 0.562/0.667; broad direction higher_loss, AUC 0.695 D/V 0.668/0.754; cross-stable False
- 65m progress_last3_slope: FP direction lower_loss, AUC 0.393 D/V 0.321/0.600; broad direction lower_loss, AUC 0.364 D/V 0.339/0.444; cross-stable False
- 35m bars_since_above_ema7: FP direction higher_loss, AUC 0.542 D/V 0.426/0.800; broad direction higher_loss, AUC 0.742 D/V 0.673/0.944; cross-stable False
- 35m longest_below_ema7: FP direction lower_loss, AUC 0.449 D/V 0.414/0.467; broad direction higher_loss, AUC 0.670 D/V 0.627/0.778; cross-stable False
- 65m end_progress_r: FP direction lower_loss, AUC 0.357 D/V 0.272/0.533; broad direction lower_loss, AUC 0.146 D/V 0.106/0.206; cross-stable False
- 35m taker_last2_mean: FP direction higher_loss, AUC 0.530 D/V 0.593/0.400; broad direction lower_loss, AUC 0.315 D/V 0.336/0.254; cross-stable False
- 65m frac_below_ema20: FP direction lower_loss, AUC 0.458 D/V 0.481/0.533; broad direction higher_loss, AUC 0.761 D/V 0.762/0.794; cross-stable False
- 35m end_progress_r: FP direction lower_loss, AUC 0.482 D/V 0.531/0.333; broad direction lower_loss, AUC 0.243 D/V 0.251/0.159; cross-stable False
- 65m longest_below_ema20: FP direction lower_loss, AUC 0.488 D/V 0.481/0.600; broad direction higher_loss, AUC 0.792 D/V 0.790/0.841; cross-stable False
- 35m longest_below_ema20: FP direction lower_loss, AUC 0.345 D/V 0.370/0.267; broad direction higher_loss, AUC 0.507 D/V 0.486/0.548; cross-stable False
- 35m frac_below_ema20: FP direction lower_loss, AUC 0.348 D/V 0.364/0.267; broad direction higher_loss, AUC 0.504 D/V 0.484/0.540; cross-stable False

## Guardrail
If an EMA20 inverse separator disappears against broad controls, treat it as control-selection artifact rather than market edge. Only cross-stable, interpretable trajectory features should be considered for a predeclared F6.22 action test.
