# BTC Temporal Saturday T-Method S5.2D — Pre-Warning Latent Runner Immunity Atlas

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — FORENSIC PASS; NO IMMUNITY RULE PROMOTED  
**Research only:** live BBC untouched

## Frozen cohort
- Exact S5.2B FLOW_EMA warning cohort: **43** = 28 discovery / 15 validation
- Latent future-deep >=+0.80: **19**
- True nondeep: **24**
- S5.2B deep-damage/nondeep-rescue parity passed before interpretation.
- Every S5.2D feature is known no later than the protect-warning decision-open.

## Main finding
There **is** pre-warning structure that separates latent future-deep runners from true nondeep warnings in the same direction in discovery and validation, but no threshold was selected and no immunity action is promoted yet.

The clearest stable pattern is **timing**:
- full latent-deep warning time median: **205m**
- full nondeep warning time median: **330m**
- discovery: **192.5m vs 285m**
- validation: **250m vs 332.5m**
- rank AUC if higher time predicts deep: full **0.345**, discovery **0.372**, validation **0.260**; therefore *earlier* warnings are more associated with latent deep runners in both halves.

The first +0.50 hinge also tends to arrive earlier on latent deep warnings:
- full median **140m vs 212.5m**
- discovery **140m vs 180m**
- validation **140m vs 235m**
- same DEEP_LOW direction in both chronology halves.

This suggests a Saturday-native mechanism: a strong runner can establish impulse relatively early, suffer a later deterioration warning, then recover. By contrast, many true nondeep warnings occur after a slower/older trade path.

## Other stable pre-warning features

### EMA20 slope at warning
Latent deep has stronger positive EMA20 slope in both halves:
- full median **+0.1427% / 60m** vs nondeep **+0.1194%**
- discovery **+0.1563% vs +0.1350%**
- validation **+0.1330% vs +0.1016%**
- AUC: full **0.629**, discovery **0.607**, validation **0.620**.

This is stable but not yet a standalone immunity rule because 40/43 warnings already have positive EMA20 slope; sign alone has little routing value.

### Post-hinge maximum close-progress before warning
Latent deep preserves/rebuilds a higher post-hinge high-water mark:
- full median **+0.5410%** vs **+0.4811%**
- discovery **+0.5303% vs +0.4921%**
- validation **+0.6293% vs +0.4791%**
- AUC: full **0.658**, discovery **0.587**, validation **0.860**.

### Post-hinge minimum close-progress before warning
Latent deep also tends to retain a higher floor before warning:
- full median **+0.2389%** vs **+0.1784%**
- discovery **+0.2429% vs +0.2155%**
- validation **+0.2134% vs +0.1523%**
- AUC: full **0.697**, discovery **0.673**, validation **0.580**.

This is important: before the generic FLOW_EMA warning, latent runners have often shown a stronger path both at the high-water mark and at the retained floor.

### EMA7 slope at warning
Same direction in both halves:
- full median **+0.0922% / 60m** vs **+0.0751%**
- discovery **+0.1060% vs +0.0864%**
- validation **+0.0905% vs +0.0751%**
- AUC full/discovery/validation: **0.575 / 0.587 / 0.560**.

Useful context, but weaker than timing and retained-path structure.

## Native-state diagnostics

### CLEAN vs prior FAILURE
CLEAN warning cohort:
- N27
- deep rate **51.9%**
- discovery **56.2%**
- validation **45.5%**.

PRIOR_FAILURE warning cohort:
- N16
- deep rate **31.2%**
- discovery **41.7%**
- validation **0%**, but validation N is only 4.

The direction supports using prior FAILURE as a negative context modifier, but validation support is too small to promote it as an immunity gate.

### EMA7 slope sign
EMA7 slope positive:
- N34
- deep rate **50.0%**
- discovery **56.5%**
- validation **36.4%**.

EMA7 slope nonpositive:
- N9
- deep rate **22.2%**
- discovery **20.0%**
- validation **25.0%**.

This sign split is directionally stable and has support in both halves, but still does not isolate latent runners strongly enough for immediate action.

## Unstable / rejected as standalone immunity inputs
The following reverse direction or fail chronological consistency and should not be used as standalone immunity rules:
- hinge taker
- hinge EMA distance
- hinge EMA slope
- raw pre-warning MFE
- warning EMA7 distance
- positive-taker-bar fraction
- post-hinge EMA20-above fraction.

This confirms again that S5.2A's hinge-flow clue should remain contextual rather than become a global hard rule.

## S5.2D verdict
**PASS as forensic evidence that latent-runner immunity is causally feasible before the warning.**

However, **NO IMMUNITY RULE IS PROMOTED YET** because:
1. the cohort is only 43 warnings / 15 validation warnings,
2. the strongest continuous signals do not yet have a predeclared routing threshold,
3. choosing a cutoff from this same sample would be post-hoc optimization.

The most important combined mechanism is:
> **EARLY PROVEN IMPULSE + EARLIER WARNING + STRONGER RETAINED POST-HINGE FLOOR/HIGH-WATER + POSITIVE EMA SLOPE**

This looks more like a temporarily deteriorating runner than a mature failed shallow trade.

## Correct continuation
Proceed to a small **S5.2E timing/path robustness study** before any action test. It should test whether the timing/path separation survives coarse, predeclared natural bins or chronological folds, without optimizing a profit threshold. If that robustness holds, only then test an immunity overlay against S5.2B.

A7.19 and A7.26 remain untouched and preserved.
