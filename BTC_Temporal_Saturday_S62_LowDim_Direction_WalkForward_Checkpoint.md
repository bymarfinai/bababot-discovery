# BTC Temporal Saturday S6.2 — Frozen Low-Dimensional Direction Candidate Test

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — CAUSAL CANDIDATE FAIL; FORENSIC SIGNAL DID NOT CONVERT TO A ROBUST LINEAR DIRECTION STRATEGY  
**Research only:** live BBC untouched

## Frozen candidate
- Features: `dist_4h_high`, `ret60`, `rv4h`.
- Model: StandardScaler + L2 logistic regression, C=1.0, probability threshold 0.50.
- Target: `SHORT_BETTER`.
- No threshold sweep, hyperparameter search, feature replacement, abstention, or post-entry information.

## Causal evaluation design
The first 55 Saturdays are warm-up only because true past-only predictions cannot exist before a training history exists.

Expanding future folds:
1. train 55 -> test 28 (indices 55–82)
2. train 83 -> test 28 (83–110)
3. train 111 -> test 28 (111–138)

Every scored Saturday is forced to choose BUY or SHORT; there is no skip.

A dedicated discovery->validation check also trains only on indices 0–82 and tests indices 83–138 (56 trades).

## Expanding walk-forward result — 84 future-scored trades
Selected direction:
- **36W / 48L = 42.86% WR**
- **+$12.990 PnL**
- expectancy **+$0.155/trade**
- PF **1.082**
- max DD **30.553**
- max loss streak **6**
- selected BUY **53** / SHORT **31**
- direction accuracy vs `SHORT_BETTER`: **53.57%**
- decisive one-direction-wins accuracy: **56.25%**

Same 84-trade baselines:
- Always BUY: **38W/84 = 45.24% WR**, **+$32.442**, PF 1.229, DD 25.745, LS5.
- Always SHORT: **26W/84 = 30.95% WR**, **-$129.282**.
- Hindsight best-direction ceiling: **64W/84 = 76.19% WR**, **+$246.406**.

Thus the causal model is positive in aggregate but **worse than the frozen BUY baseline in both WR and PnL**.

## Fold-by-fold
### Fold 1 — train 55 -> test 28
- selected: **42.86% WR / +$11.069**
- BUY: **46.43% / -$2.091**
- SHORT: **28.57% / -$32.654**
- direction accuracy **50.00%**

The model adds PnL versus both baselines here despite lower WR than BUY.

### Fold 2 — train 83 -> test 28
- selected: **42.86% / +$8.873**
- BUY: **35.71% / +$0.954**
- SHORT: **35.71% / -$34.907**
- direction accuracy **57.14%**

This is the strongest causal fold: selected direction improves both PnL and WR versus either single-direction baseline.

### Fold 3 — train 111 -> test 28
- selected: **42.86% / -$6.953**
- BUY: **53.57% / +$33.579**
- SHORT: **28.57% / -$61.721**
- direction accuracy **53.57%**

This fold reverses the economic value: the model unnecessarily flips too many Saturdays away from a strong BUY regime.

## Dedicated frozen discovery -> validation holdout
Train 83, test 56:
- selected: **24W/56 = 42.86% WR**, **+$9.694**, PF 1.092, DD 22.234, LS6.
- Always BUY: **25W/56 = 44.64%**, **+$34.533**.
- Always SHORT: **18W/56 = 32.14%**, **-$96.628**.
- Hindsight best direction: **43W/56 = 76.79%**, **+$163.064**.
- model selected BUY **40** / SHORT **16**.
- direction accuracy **55.36%**; decisive-only **55.81%**.

So the frozen 3-feature candidate does **not** transfer economically to the 56-trade validation block.

## Mechanism sign stability
Standardized coefficients across the three walk-forward fits:
- `dist_4h_high` expected positive for SHORT preference: **+0.610, -0.024, +0.180** -> expected sign 2/3.
- `ret60` expected positive: **+0.790, +0.555, +0.466** -> 3/3.
- `rv4h` expected negative: **-0.210, -0.261, -0.220** -> 3/3.

Thus S6.1's broad mechanism is not entirely spurious: momentum and quietness retain the expected coefficient direction. But coefficient-direction stability is **not sufficient for profitable forced direction selection**.

## Predeclared gate
- Walk-forward WR beats both baselines: **FAIL**.
- Walk-forward PnL beats both baselines: **FAIL**.
- Validation PnL beats both baselines: **FAIL**.
- Mechanism signs match >=2/3 folds: **PASS**.

**S6.2 CAUSAL CANDIDATE: FAIL.**

## Critical interpretation
S6.0 and S6.1 remain valid as capacity/forensic findings:
- there is a large hindsight BUY-vs-SHORT opportunity;
- several pre-entry features contain stable direction information.

But S6.2 proves that simply feeding one representative feature from each dimension into a linear probability model is **not enough**. The important failure is not lack of oracle capacity — the same 84 future-scored timestamps still have a **76.19% hindsight best-direction WR ceiling**. The failure is converting that capacity into a causal decision boundary.

The last 28-trade fold is especially diagnostic: always-BUY became very strong (53.57% WR / +$33.579), while the model still selected 12 SHORTs and lost value. This suggests the pre-entry effect is likely **state-dependent / nonlinear / interaction-based**, rather than a globally stable linear relationship such as 'more bullish extension = more SHORT'.

Do NOT repair this result post hoc by changing C, probability threshold, feature set, warm-up, or fold boundaries in S6.2.

## Research decision
- Keep S5.7G `NO_BULL_TOP_Q_30` as the provisional same-sample full-coverage Saturday management champion.
- Keep S6.0 oracle capacity and S6.1 feature atlas as research evidence.
- Reject this exact S6.2 3-feature linear classifier as a deployable direction selector.
- Do not combine it with S5.7G.
- No live BBC modification.

A clean next milestone, if continuing, is a **frozen S6.3 direction-error/state interaction forensic**: inspect where the 3-feature model makes costly false SHORT/false BUY decisions using only the already-frozen features and broader pre-entry state families from S6.1, without fitting a new model yet. The goal would be to determine whether the edge is conditional/nonlinear before attempting another causal candidate.

## Execution
- Successful workflow run: **32033024888**
- Artifact: `s62-output`, ID **9289634833**
- Script: `research/s62_lowdim_direction_walkforward.py`
