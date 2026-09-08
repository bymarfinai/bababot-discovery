# SOL Discovery State

> Authoritative operational checkpoint for the SOL discovery lineage. This summarizes frozen state and the current scientific frontier; canonical preregistrations, deterministic result artifacts, and scientific verdict documents remain authoritative for each experiment.

## Baseline

- Pair: `SOL`
- Discovery branch: `research/sol-long-structure-a1-run`
- State originally established from commit: `12c483959af3ac87c63d671f7b2edccb2fed2218`
- Latest completed experiment: **`A66`**
- Next available experiment ID: **`A67`**
- Pair-native rule: **copy the discovery grammar, never copy the coordinates**.

`A67` is an identifier only. No A67 hypothesis, feature family, comparator, threshold, intervention, or promotion gate is approved by this state update.

## Frozen execution parent

`R360 / 15UTC / E0_RESTING_H -> E40`

Do not retune range, clock, entry, or target in response to A62-A66 unless a future experiment is explicitly preregistered as a parent-recalibration lineage.

## Frozen mature universe

| Partition | Parent | CENTRAL losses | L0 / M0 | M1 | Raw winners |
|---|---:|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 58 | 244 |
| External Validation | 281 | 166 | 13 | 16 | 115 |
| Reference Validation | 337 | 187 | 26 | 21 | 150 |
| **Pooled** | **1,219** | **710** | **76** | **95** | **509** |

- `L0 = NEVER_BREAK_REFERENCE_INVALIDATION`
- Deterministic mechanism: `M0_REFERENCE_INVALIDATION`
- `M1 = M1_TIME_NO_STRUCTURAL_FAIL`
- External and Reference Validation are never tuning sets.
- Cohort identity cannot be redefined from newly observed features.

## Scientific protocol

Every experiment follows:

1. preregister the scientific question, frozen inputs, finite feature/search family, support rules, and success criteria;
2. commit preregistration before implementation;
3. implement and run through CI;
4. persist deterministic result artifacts;
5. write a separate scientific verdict without post-hoc rescue;
6. advance state manually only after the verdict.

Descriptive anatomy, mechanism specificity, economic feasibility, and production deployment are separate stages.

## A62-A66 lineage

### A62 — Early-progress anatomy

**SUPPORTED.** At 60m and 120m, L0/M0 showed replicated deeper `running_mae_R`, weaker `close_H_R`, and larger `drawdown_from_best_R` versus age/state-matched eventual winners. A62 was descriptive only.

Result persistence: `aabdbd16514c027fe7f81fe8ecf84db589eea3da`  
Verdict: `37f9c233baa0ad34c613c5fbaa67276c4cb625a3`

### A63 — Mechanism specificity

**SUPPORTED.** Against frozen M1 never-break losses, only **`running_mae_R`** survived the strict 2-of-2 specificity rule at both 60m and 120m across Development and both OOS partitions. `close_H_R` and `drawdown_from_best_R` did not.

Result persistence: `3a8a276b31988201070c30833bd2809b45b69145`  
Verdict: `c192ba3469a685e074c2712887212fbc4f65a69c`

### A64 — Static MAE economic translation

**REJECTED AT DEVELOPMENT.** Six preregistered static full-exit candidates crossed 60m/120m with Development L0 Q25/Q50/Q75 MAE thresholds. All improved Development net PnL and PF diagnostically, but none preserved the frozen 5bps stressed WR baseline. No rule was selected and OOS intervention economics remained unopened.

The strongest diagnostic, `A120_Q25`, produced approximately +$86.29 Development delta net and +$165.54 L0 PnL delta, but damaged eventual-winner PnL by about -$76.38 and reduced stressed WR. It remains diagnostic only and cannot be rescued.

Result persistence: `ad8ecdba677ed0f96b004507535c2c3d5b78a18a`  
Verdict: `27368e56c3966f071e54f2c79d56d56a2faa418a`

### A65 — MAE-conditioned simple recovery anatomy

**INCONCLUSIVE.** L0/M0 cases were matched to eventual winners on nearest `running_mae_R` severity at the same age. Four simple recovery families (`recovery_from_worst_R`, `recovery_efficiency`, `bars_since_worst_fraction`, `post_worst_close_slope_R_per_bar`) failed strict 2-of-2 replication at 60m and 120m.

This closed the simple story that severe-MAE winners are robustly distinguishable from L0 merely because they rebound more, recover more efficiently, hit the worst earlier, or have a stronger post-worst slope.

Result persistence: `e0955aad2084f1d654b2c363656d0e686583d316`  
Verdict: `2d6dbef9985c075dcd5c038cdd859551f7f78e8e`

## Latest completed experiment — A66

### A66 question

**L0 MAE-CONDITIONED RECLAIM SEQUENCE ANATOMY**

> Holding early adverse-excursion severity approximately constant, does the sequence by which price reclaims and sustains ground after the snapshot worst excursion distinguish genuine L0/M0 reference-invalidation losses from eventual winners at the same 60m or 120m age?

A66 retained A65's MAE-conditioned matching and moved from simple static recovery descriptors to a finite sequence/path-geometry family anchored on the first snapshot worst low and a fixed 50% half-reclaim level.

### Matching and support

Every fixed cell exceeded the preregistered support floor:

| Partition | Age | Eligible L0 | Matched | Unique winners | Max reuse | Median abs MAE gap |
|---|---:|---:|---:|---:|---:|---:|
| Development | 60m | 33 | 33 | 20 | 5x | 0.049R |
| Development | 120m | 29 | 29 | 13 | 5x | 0.056R |
| External Validation | 60m | 12 | 12 | 9 | 2x | 0.009R |
| External Validation | 120m | 11 | 11 | 8 | 3x | 0.029R |
| Reference Validation | 60m | 22 | 22 | 17 | 3x | 0.007R |
| Reference Validation | 120m | 19 | 19 | 11 | 4x | 0.006R |

Raw SOLUSDT 5m coverage remained **99.7671%**.

### A66 finite sequence family

Only these preregistered features were tested:

- `max_reclaim_fraction_of_mae`
- `half_reclaim_latency_fraction`
- `longest_half_reclaim_run_fraction`
- `post_half_reclaim_hold_fraction`
- `late_mae_extension_fraction`

The fixed half-reclaim level was 50% of the snapshot adverse excursion. It was descriptive and never Development-optimized.

### A66 verdict

**`SOL_LONG_15UTC_L0_MAE_CONDITIONED_RECLAIM_SEQUENCE_A66_INCONCLUSIVE`**

No sequence family passed strict 2-of-2 replication.

At 60m, four reclaim/hold features showed large Development and External separation in the preregistered direction, but Reference Validation showed **0.000 median gap / 0.000 effect** for the same features. Development block consistency was also only `3/4` for those families.

At 120m, several Development directions reversed while External/Reference often pointed in the hypothesized direction. This cross-partition instability prevents a stable mechanistic interpretation.

`late_mae_extension_fraction` is specifically **not** a rescue candidate. At 120m it had positive gaps/effects across Development (`+0.216 / 0.620`), External (`+0.179 / 0.372`), and Reference (`+0.357 / 0.711`), but Development block consistency was only `2/3`; at 60m the block rule was `2/4` and Reference separation was zero. The frozen gate therefore rejects it.

Result persistence: `6f7a95bb7a44af8031fcca3d2e0196a0c48501e2`  
Scientific verdict: `5a631f61b1cff5f13dccbadfaa17ae2dcc863e9a`

### A66 scientific meaning

The narrow supported lineage statement is now:

> **Adverse-excursion depth remains a replicated L0/M0-specific early research axis, but neither A65's simple post-worst recovery descriptors nor A66's fixed half-reclaim sequence/hold geometry robustly explains why some severe-MAE trades remain recoverable winners while genuine L0/M0 proceeds to reference invalidation.**

This does not invalidate A62/A63 and does not rehabilitate A64. It closes the exact adjacent recovery/reclaim families tested in A65-A66.

## Closed or strongly constrained routes

Do not casually reopen:

- `A43-A44`: portfolio/week-state;
- `A45`: pre-range filter;
- `A46`: failed entry/target recalibration;
- `A47`, `A47B -> A47C`: pre-entry separator and failed economic gate translation;
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
- `A63`: promoting `close_H_R` or `drawdown_from_best_R` as strict L0-specific mechanisms;
- `A64`: static 60/120m MAE full-exit Q25/Q50/Q75 family, gate relaxation, threshold/age rescue, or OOS rescue;
- `A65`: exact simple MAE-conditioned recovery family or post-hoc composite;
- `A66`: exact fixed-50%-half-reclaim sequence family;
- `A66`: retuning half-reclaim to 25%, 75%, or another neighboring level;
- `A66`: selecting favorable 60m Development + External while ignoring Reference;
- `A66`: rescuing `late_mae_extension_fraction` by relaxing Development block consistency.

## Durable lessons

1. Replicated anatomy is not automatically an executable rule (`A47B -> A47C`, `A55 -> A56`).
2. OOS gates are essential; Development improvement can reverse or fail robustness (`A59`).
3. L0/M0 has real early deterioration and `running_mae_R` is the robust mechanism-specific axis (`A62-A63`).
4. MAE contains economic information, but static full exit is too blunt under the frozen objective (`A64`).
5. The eventual-winner retention problem is not robustly explained by simple post-worst recovery descriptors (`A65`).
6. It is also not robustly explained by the tested fixed half-reclaim timing/hold sequence (`A66`).
7. Repeatedly mining neighboring recovery/reclaim metrics is now scientifically weak; the next lineage should represent a genuine mechanism reset.

## Current frontier

The frontier is a **manual post-A66 winner-retention mechanism reset**.

Core question:

> What genuinely new pair-native causal information, outside the tested simple post-worst recovery and fixed half-reclaim sequence families, explains why some severe-MAE trades remain recoverable eventual winners while genuine L0/M0 proceeds to reference invalidation?

`A67` is only the next available identifier. It is **not** preapproved as a new MAE threshold search, a relaxed A64 rerun, a partial/re-arm version of `A120_Q25`, an A65 failed-feature composite, a different reclaim percentage, a rescue of `late_mae_extension_fraction`, or an OOS look at a rejected intervention candidate.

Live intervention remains prohibited.

## Automation boundary

Automation may own reproducible plumbing: registry validation, experiment paths, frozen invariant assertions, preregistration-history guards, deterministic result envelopes, CI execution, and artifact persistence.

Automation must not decide the next scientific hypothesis, rescue a failed candidate, relax a gate post hoc, select features after validation inspection, make the substantive scientific verdict, or advance state automatically.

## Update policy

Update this state only after result persistence and a separate scientific verdict. A CI run alone must never advance scientific state.
