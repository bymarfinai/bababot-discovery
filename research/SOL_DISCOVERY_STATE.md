# SOL Discovery State

> Authoritative operational checkpoint for the SOL discovery lineage. This file summarizes frozen state and the current scientific frontier; it does **not** replace experiment preregistrations, deterministic result artifacts, or scientific verdict documents.

## Baseline

- Pair: `SOL`
- Discovery branch: `research/sol-long-structure-a1-run`
- State originally established from commit: `12c483959af3ac87c63d671f7b2edccb2fed2218`
- Latest completed experiment: **`A65`**
- Next available experiment ID: **`A66`**
- Pair-native rule: **copy the discovery grammar, never copy the coordinates**.

`A66` is an identifier only. No A66 hypothesis, feature family, threshold, comparator, intervention, or promotion gate is approved by this state update.

## Frozen execution parent

The execution parent remains:

`R360 / 15UTC / E0_RESTING_H -> E40`

Do not retune range, clock, entry, or target in response to A62-A65 unless a future experiment is explicitly preregistered as a parent-recalibration lineage.

## Frozen mature loss universe

| Partition | Parent | CENTRAL losses | L0 / M0 | M1 | Raw winners |
|---|---:|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 58 | 244 |
| External Validation | 281 | 166 | 13 | 16 | 115 |
| Reference Validation | 337 | 187 | 26 | 21 | 150 |
| **Pooled** | **1,219** | **710** | **76** | **95** | **509** |

- `L0 = NEVER_BREAK_REFERENCE_INVALIDATION`
- Deterministic runner mechanism: `M0_REFERENCE_INVALIDATION`
- `M1 = NEVER_BREAK_TIME / M1_TIME_NO_STRUCTURAL_FAIL`
- External Validation and Reference Validation must never be merged into Development or used for tuning.
- Cohort identity must not be redefined from newly observed features.

## Scientific protocol

Every scientific experiment follows:

1. preregister the question, frozen inputs, finite search family, support rules, and success criteria;
2. commit preregistration before implementation;
3. implement and run through CI;
4. persist deterministic result artifacts;
5. write a separate scientific verdict without post-hoc rescue or retuning;
6. advance discovery state manually only after the verdict is complete.

Descriptive anatomy, mechanism specificity, economic feasibility, and production deployment are separate stages.

## A62 — Early-progress anatomy

Verdict: **`SOL_LONG_15UTC_L0_EARLY_PROGRESS_A62_SUPPORTED`**.

At 60m and 120m, three feature families replicated across Development and both OOS partitions: deeper `running_mae_R`, weaker `close_H_R`, and larger `drawdown_from_best_R`. A62 was descriptive only.

Result persistence commit: `aabdbd16514c027fe7f81fe8ecf84db589eea3da`.
Scientific verdict commit: `37f9c233baa0ad34c613c5fbaa67276c4cb625a3`.

## A63 — Early-progress specificity

Verdict: **`SOL_LONG_15UTC_L0_EARLY_PROGRESS_SPECIFICITY_A63_SUPPORTED`**.

A63 compared L0/M0 with the frozen M1 never-break loss mechanism at 60m and 120m. Only **`running_mae_R`** survived the strict 2-of-2 specificity rule across Development and both OOS partitions. `close_H_R` and `drawdown_from_best_R` did not.

Result persistence commit: `3a8a276b31988201070c30833bd2809b45b69145`.
Scientific verdict commit: `c192ba3469a685e074c2712887212fbc4f65a69c`.

## A64 — Early MAE economic translation

Verdict: **`SOL_LONG_15UTC_L0_EARLY_MAE_ECONOMIC_TRANSLATION_A64_REJECTED_DEVELOPMENT`**.

A64 tested six preregistered static full-exit candidates: 60m/120m crossed with Development L0 Q25/Q50/Q75 `running_mae_R` thresholds. All six improved Development net PnL and PF diagnostically, but zero passed every frozen promotion gate. The common decisive failure was deterioration of 5bps stressed WR below the frozen Development baseline. No candidate was promoted and OOS intervention economics correctly remained unopened.

`A120_Q25` remains diagnostic only; it cannot be rescued, partialized, rearmed, threshold-shifted, or promoted post hoc.

Result persistence commit: `ad8ecdba677ed0f96b004507535c2c3d5b78a18a`.
Scientific verdict commit: `27368e56c3966f071e54f2c79d56d56a2faa418a`.

## Latest completed experiment — A65

### A65 question

**L0 MAE-CONDITIONED WINNER RECOVERY ANATOMY**

> Holding early adverse-excursion severity approximately constant, what causal recovery-path behavior distinguishes genuine L0/M0 reference-invalidation losses from eventual parent winners that are still live and pre-break at the same 60m or 120m age?

A65 directly addressed A64's winner-retention tension mechanistically rather than relaxing the rejected A64 economic gate.

### Frozen comparator and matching

Eligible L0/M0 cases were matched to eventual parent winners at the same fixed age and partition. Development also required the same frozen `dev_block`. The selected control minimized absolute `running_mae_R` distance, with deterministic tie-breaks. Control reuse was preregistered and reported.

All fixed snapshots met the preregistered support floor:

| Partition | Age | Eligible L0 | Matched | Unique controls | Max reuse | Median abs MAE gap |
|---|---:|---:|---:|---:|---:|---:|
| Development | 60m | 33 | 33 | 20 | 5x | 0.049R |
| Development | 120m | 29 | 29 | 13 | 5x | 0.056R |
| External Validation | 60m | 12 | 12 | 9 | 2x | 0.009R |
| External Validation | 120m | 11 | 11 | 8 | 3x | 0.029R |
| Reference Validation | 60m | 22 | 22 | 17 | 3x | 0.007R |
| Reference Validation | 120m | 19 | 19 | 11 | 4x | 0.006R |

Raw SOLUSDT 5m coverage remained **99.7671%**.

### A65 finite feature family

Only four preregistered simple recovery descriptors were tested:

- `recovery_from_worst_R`
- `recovery_efficiency`
- `bars_since_worst_fraction`
- `post_worst_close_slope_R_per_bar`

The preregistered L0/M0 direction was lower for every family. A feature had to fully replicate at **both 60m and 120m** after Development eligibility and both OOS gates.

### A65 verdict

**`SOL_LONG_15UTC_L0_MAE_CONDITIONED_RECOVERY_A65_INCONCLUSIVE`**

No feature family satisfied strict 2-of-2 replication.

| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |
|---:|---|---:|---:|---:|---:|---|
| 60m | `recovery_from_worst_R` | -0.071 / 0.371 | 2/4 | -0.071 / 0.403 | +0.026 / 0.209 | NO |
| 60m | `recovery_efficiency` | -0.307 / 0.575 | 2/4 | -0.562 / 1.043 | -0.009 / 0.028 | NO |
| 60m | `bars_since_worst_fraction` | 0.000 / 0.000 | 2/4 | -0.200 / 0.356 | -0.150 / 0.261 | NO |
| 60m | `post_worst_close_slope_R_per_bar` | -0.026 / 0.547 | 3/4 | -0.004 / 0.134 | +0.003 / 0.085 | NO |
| 120m | `recovery_from_worst_R` | +0.118 / 0.368 | 1/3 | -0.029 / 0.122 | -0.174 / 0.630 | NO |
| 120m | `recovery_efficiency` | +0.046 / 0.085 | 2/3 | -0.569 / 0.886 | -0.354 / 0.889 | NO |
| 120m | `bars_since_worst_fraction` | +0.182 / 0.471 | 1/3 | -0.182 / 0.327 | -0.364 / 0.800 | NO |
| 120m | `post_worst_close_slope_R_per_bar` | -0.009 / 0.254 | 2/3 | -0.004 / 0.198 | -0.016 / 0.667 | NO |

This is not a technical or support failure. At 120m, three families reverse the preregistered direction in Development while often pointing the hypothesized way OOS. `post_worst_close_slope_R_per_bar` remains directionally negative but misses the frozen Development effect and block gates. These inconsistencies prohibit a favorable post-hoc interpretation.

### A65 scientific meaning

The narrow conclusion is:

> **After approximately conditioning on MAE severity, the tested simple post-worst recovery descriptors do not robustly explain why some severe-MAE trades remain recoverable eventual winners while genuine L0/M0 proceeds to reference invalidation.**

A65 does not invalidate A62/A63 and does not rehabilitate A64. It closes the exact simple recovery family under the frozen A65 design.

Result persistence commit: `e0955aad2084f1d654b2c363656d0e686583d316`.
Scientific verdict commit: `2d6dbef9985c075dcd5c038cdd859551f7f78e8e`.

## Closed or strongly constrained routes

Do not casually reopen:

- `A43-A44`: portfolio/week-state route;
- `A45`: pre-range filter;
- `A46`: failed entry/target recalibration route;
- `A47`: conventional pre-entry quality;
- `A47B -> A47C`: descriptive separator -> failed economic gate;
- `A48`: participation/volume;
- `A49`: BTC/ETH alignment for SOL;
- `A52-A53`: generic warning -> hard guard;
- `A54`: post-H05/H10 secondary trigger;
- `A55 -> A56`: terminal-near anatomy -> failed executable guard;
- `A58`: universal 1m intrabar separator;
- `A59`: H05 hybrid partial derisk/re-arm;
- `A60`: 1m range compression;
- `A61`: LOW_MFE H05 prewarning retune;
- `A62`: direct anatomy-to-intervention conversion;
- `A63`: `close_H_R` or `drawdown_from_best_R` as strict 2-of-2 L0-specific mechanisms;
- `A64`: static 60/120m MAE full-exit Q25/Q50/Q75 family and all post-hoc gate/threshold/age rescue;
- `A65`: the exact four-feature MAE-conditioned simple recovery family;
- `A65`: post-hoc composite of failed recovery descriptors;
- `A65`: retuning directions, effect floors, support floors, ages, or matching after result inspection.

## Durable lessons

1. **A47B -> A47C:** replicated structure does not imply a profitable gate.
2. **A55 -> A56:** predictive failure anatomy does not imply a profitable live exit.
3. **A59:** Development economics can reverse OOS; OOS gates remain essential.
4. **A62:** genuine early deterioration exists around 60-120m.
5. **A63:** the robust L0-specific early axis narrows to `running_mae_R`.
6. **A64:** mechanism-specific information can improve PnL/PF/DD while failing promotion because eventual-winner retention and stressed WR deteriorate.
7. **A65:** after approximately holding MAE severity constant, simple post-worst rebound descriptors do not provide a robust additional discriminator. The winner-retention problem is more structural than this recovery-feature family captured.

## Current frontier

The frontier is now a **manual post-A65 winner-retention structure decision**.

Core question:

> What genuinely new pair-native causal structure distinguishes severe-MAE trades that remain recoverable eventual winners from genuine L0/M0 reference-invalidation losses, given that static MAE full exit failed A64 promotion and simple post-worst recovery descriptors failed A65 strict replication?

This remains a mechanistic question before another intervention question.

`A66` is only the next available identifier. It is **not** preapproved as:

- a new MAE threshold search;
- a relaxed-WR rerun of A64;
- a partial/re-arm version of `A120_Q25`;
- an OOS look at an A64 rejected candidate;
- a composite of A65 failed recovery features;
- a threshold derived from an A65 median;
- a resurrection of A63-rejected `close_H_R` or `drawdown_from_best_R`.

Any A66 must be a genuinely new preregistered pair-native mechanism hypothesis.

## Automation boundary

Automation may own reproducible plumbing: registry validation, experiment IDs/paths, frozen invariant assertions, preregistration-history guards, deterministic result envelopes, CI execution, and artifact persistence.

Automation must not decide the next scientific hypothesis, rescue a failed candidate, relax a gate post hoc, select features after validation inspection, write substantive interpretation automatically, make the scientific verdict, or advance state automatically.

## Update policy

Update this state only after result persistence and a separate scientific verdict. A CI run alone must never advance scientific state.
