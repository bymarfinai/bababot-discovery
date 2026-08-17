# BTC Temporal Friday F6.0 — Adaptive Restart Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — FORENSIC PASS; STRONG FRIDAY-NATIVE ADAPTIVE STATE STRUCTURE FOUND; NO NEW ACTION RULE YET  
**Research only:** live BBC untouched

## Frozen parent parity
Friday 15:00 WIB BUY, TP +2.0%, SL -0.7%, max hold 6h, $500 fixed notional and $0.75 round-trip fee.

- N **138**
- **66W / 72L = 47.83% WR**
- PnL **+$64.630**
- Discovery (82): **54.88% WR / +$99.194**
- Validation (56): **37.50% WR / -$34.563**

The old Friday chronology problem is therefore reproduced exactly.

## Friday-native R geometry
Frozen risk unit is **R = 0.70%**.

Natural favorable-proof landmarks:
- **+0.35% = 0.5R**
- **+0.70% = 1R**
- **+1.40% = 2R**

These landmarks were chosen from the frozen Friday risk geometry, not copied from Saturday thresholds.

## The first major adaptive finding: proof-of-strength is extremely informative
### Reached +0.5R (+0.35%)
- reached: **97 trades**, **67.01% WR**, **+$204.912**
  - Discovery: 64 trades, **68.75% WR**, +$157.401
  - Validation: 33 trades, **63.64% WR**, +$47.512
- never reached: **41 trades**, **2.44% WR**, **-$140.282**
  - Discovery: 18 trades, **5.56% WR**, -$58.207
  - Validation: 23 trades, **0.00% WR**, -$82.075

### Reached +1R (+0.70%)
- reached: **71 trades**, **78.87% WR**, **+$252.135**
  - Discovery: 45 trades, **82.22% WR**, +$190.429
  - Validation: 26 trades, **73.08% WR**, +$61.706
- never reached: **67 trades**, **14.93% WR**, **-$187.504**
  - Discovery: 37 trades, 21.62% WR, -$91.235
  - Validation: 30 trades, **6.67% WR**, -$96.269

### Reached +2R (+1.40%)
- reached: **30 trades**, **100.00% WR**, **+$230.684**
  - Discovery: 23/23 winners
  - Validation: 7/7 winners
- not reached: 108 trades, 33.33% WR, -$166.054

The 2R result is descriptive/hindsight path proof, not a causal entry rule.

## Post-0.5R path
After +0.5R is first causally knowable:
- `GRADUATE_1R_FIRST`: **60 trades**, **76.67% WR**, **+$202.917**
  - D: 78.95% WR / +$154.328
  - V: 72.73% WR / +$48.588
- `GIVEBACK_ZERO_FIRST`: 34 trades, 47.06% WR, -$1.193
  - D: 50.00% / +$2.108
  - V: 40.00% / -$3.301
- `NO_05R`: 41 trades, **2.44% WR**, -$140.282
- `HOLD_POSITIVE`: 3 trades, 100% WR, +$3.189

This suggests Friday has a genuine adaptive progression rather than a single static BUY quality.

## Causal snapshot separation
Winner-separation AUCs use only completed information before the decision open.

### +30m
- progress: **0.719 full / 0.658 D / 0.807 V**
- MFE: **0.697 / 0.652 / 0.734**
- taker flow: **0.685 / 0.671 / 0.694**
- EMA7 distance: **0.680 / 0.594 / 0.794**

### +60m — strongest clean adaptive hinge
- progress: **0.756 full / 0.680 D / 0.859 V**
- MFE: **0.753 / 0.687 / 0.861**
- taker flow: **0.672 / 0.641 / 0.672**
- EMA20 distance: **0.638 / 0.573 / 0.730**
- EMA spread: **0.624 / 0.579 / 0.688**
- MAE is inversely predictive: **0.348 / 0.371 / 0.312**

### +120m
- progress: **0.756 / 0.691 / 0.853**
- MFE: **0.761 / 0.699 / 0.874**
- EMA spread: **0.659 / 0.580 / 0.776**
- taker: 0.619 / 0.625 / 0.605

Thus the separation strengthens rather than disappears in validation.

## Post-run natural sign-state diagnostic at +60m
This is **not a predeclared action rule** and is therefore NOT promoted yet. It is a natural, non-optimized conjunction inspected after F6.0 to identify the next candidate state:

`HEALTHY_60 = alive at +60m AND progress > 0 AND recent taker flow > 0 AND completed close > EMA20`

`FAILURE_60 = alive at +60m AND progress <= 0 AND recent taker flow < 0 AND completed close <= EMA20`

Everything else = MIXED.

Results among trades still alive at +60m:

### HEALTHY_60
- **41 trades**
- **30W / 11L = 73.17% WR**
- **+$128.131**
- Discovery: 29 trades, **68.97% WR**, +$85.888
- Validation: 12 trades, **83.33% WR**, +$42.242

Four chronological blocks:
- Fold 1: 13 trades, **69.23% WR**, +$42.455
- Fold 2: 11 trades, **72.73% WR**, +$34.220
- Fold 3: 9 trades, **77.78% WR**, +$23.473
- Fold 4: 8 trades, **75.00% WR**, +$27.983

This is exceptionally stable descriptively: all four folds are positive and roughly 69–78% WR.

### FAILURE_60
- **28 trades**
- **7W / 21L = 25.00% WR**
- **-$44.485**
- Discovery: 15 trades, **26.67% WR**, -$11.150
- Validation: 13 trades, **23.08% WR**, -$33.335

Four folds:
- F1: 20.00% WR / -$11.112
- F2: 37.50% WR / +$2.729
- F3: 14.29% WR / -$16.586
- F4: 25.00% WR / -$19.517

### MIXED_60
- 54 trades
- **53.70% WR**, +$44.735
- Discovery: 67.74% WR / +$54.206
- Validation: 34.78% WR / -$9.471

The MIXED cohort is where the old chronology instability remains concentrated.

## Important early-exit fact
By +60m, **15 trades had already exited** under the frozen parent, and all **15 were losses** (early SLs). This reinforces that the first hour is the key Friday thesis-health window.

## Pre-entry context
Pre-entry features are weaker than post-entry path health, but several directions are D/V-consistent:
- prior 60m return AUC: **0.355 full / 0.328 D / 0.407 V**
- entry EMA spread: **0.358 / 0.357 / 0.351**
- 1h range location: **0.334 / 0.294 / 0.405**
- 4h high distance: **0.426 / 0.431 / 0.434**

For the fixed Friday BUY temporal prior, weaker/less-extended pre-entry bullish structure is descriptively more winner-like. However, pre-entry separation is materially weaker than the +60m adaptive state.

## Interpretation
Friday appears to be a much cleaner **adaptive thesis-health** problem than the earlier F5 warning branch suggested:

> temporal BUY prior -> observe first hour -> state separates sharply into HEALTHY / MIXED / FAILURE.

The strongest finding is not a hidden warning or a static filter. It is **proof/acceptance after entry**:
- +0.5R proof already raises historical WR to ~67%;
- +1R proof raises it to ~79%;
- the causal natural HEALTHY_60 state is ~73% WR and transfers strongly D/V and 4 chronological folds;
- FAILURE_60 is ~25% WR.

This is much closer to the user's desired adaptive behavior than the old F5 threshold/filter approach.

## What is NOT yet allowed
- Do not claim HEALTHY_60 as a deployable rule yet because the exact conjunction was inspected post-run.
- Do not cut all FAILURE_60 trades yet.
- Do not skip non-HEALTHY Fridays; coverage objective remains important.
- Do not change TP2.0 / SL0.7 / 6h yet.
- Do not revive F5.12/F5.16 thresholds automatically.

## Next clean milestone
**F6.1 — Frozen +60m Thesis-State Management Counterfactual** should predeclare and freeze the natural sign-state exactly as written above, then test management alternatives without threshold sweep.

The first question should be narrow:
> when `FAILURE_60` is present, does an actual-open exit at +60m improve PnL/WR versus the frozen parent in both D and V, while HEALTHY_60 remains untouched?

A secondary forensic can follow MIXED_60 evolution to +120m only after the FAILURE_60 test is completed.

## Execution
- Successful workflow run: **32035179615**
- Artifact: `f60-output`, ID **9290394479**
- Workflow commit: `6d374b1d9119da086690f9f9f392fb59b7893af3`
- Script: `research/f60_friday_adaptive_restart_atlas.py`
- No live BBC modification.
