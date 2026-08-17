# Friday F6.21 — Low-Giveback Trajectory Persistence Forensic

**Status: COMPLETE — FORENSIC ONLY; NO EXIT RULE TUNED/PROMOTED.**
**Live BBC untouched; frozen FIB5/EARLY10/F6.5/D3 unchanged.**

## Cohorts
- low givebacks: **12**
- F6.20 false-positive eventual winners (union): **14** (D 9 / V 5)
- broad eligible winner controls: **65**

## Stable primary separators (loss vs F6.20 false-positive winner)
- 65m taker_last2_mean: AUC 0.292, D 0.309, V 0.267; lower_loss; median loss -0.0630 vs ctrl 0.0010
- 35m longest_below_ema20: AUC 0.345, D 0.370, V 0.267; lower_loss; median loss 0.0000 vs ctrl 1.5000
- 35m frac_below_ema20: AUC 0.348, D 0.364, V 0.267; lower_loss; median loss 0.0000 vs ctrl 0.2143

## Interpretation guardrail
This stage describes persistence/recovery trajectories only. It does not choose a cut threshold or management action. Any F6.22 rule must be predeclared from a small interpretable subset of stable trajectory features and then replayed chronologically against the frozen stack.
Do not retune the 35/65m horizons on this sample.
