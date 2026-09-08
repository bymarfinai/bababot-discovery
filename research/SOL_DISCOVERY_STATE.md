# SOL Discovery State

> Authoritative operational checkpoint for the SOL discovery lineage. This file summarizes frozen state and the current scientific frontier; it does **not** replace experiment preregistrations, deterministic result artifacts, or scientific verdict documents.

## Baseline

- Pair: `SOL`
- Discovery branch: `research/sol-long-structure-a1-run`
- State originally established from commit: `12c483959af3ac87c63d671f7b2edccb2fed2218`
- Latest completed experiment: **`A64`**
- Next available experiment ID: **`A65`**
- Pair-native rule: **copy the discovery grammar, never copy the coordinates**.

`A65` is an identifier only. No A65 hypothesis, feature, threshold, age, comparator, intervention, or promotion gate is approved by this state update.

## Frozen execution parent

The execution parent remains:

`R360 / 15UTC / E0_RESTING_H -> E40`

Do not retune range, clock, entry, or target in response to A62-A64 results unless a future experiment is explicitly preregistered as a parent-recalibration lineage.

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

A62 compared frozen L0/M0 losses against age/state-matched eventual winners at fixed 30m, 60m, and 120m snapshots.

The 30m snapshot did not establish a robust family. At 60m and 120m, three feature families replicated across Development and both OOS partitions:

- `running_mae_R`: deeper adverse excursion;
- `close_H_R`: weaker location relative to H;
- `drawdown_from_best_R`: larger giveback from best post-entry excursion.

A62 was descriptive anatomy only. No executable threshold was authorized.

Result persistence commit: `aabdbd16514c027fe7f81fe8ecf84db589eea3da`.
Scientific verdict commit: `37f9c233baa0ad34c613c5fbaa67276c4cb625a3`.

## A63 — Early-progress specificity

Verdict: **`SOL_LONG_15UTC_L0_EARLY_PROGRESS_SPECIFICITY_A63_SUPPORTED`**.

A63 asked whether the A62 pattern was specifically L0/M0 rather than a generic never-break loser signature. The frozen comparator was `M1_TIME_NO_STRUCTURAL_FAIL`; only the three A62-supported families and only 60m/120m were carried forward.

Only **`running_mae_R`** survived the strict 2-of-2 mechanism-specificity rule.

### `running_mae_R`

At 60m:

- Development: L0-minus-M1 median gap `+0.222R`, effect `1.219`, block direction `4/4`;
- External: `+0.114R`, effect `0.545`;
- Reference: `+0.320R`, effect `0.798`.

At 120m:

- Development: `+0.216R`, effect `1.235`, block direction `3/3`;
- External: `+0.206R`, effect `0.969`;
- Reference: `+0.240R`, effect `0.655`.

`close_H_R` did not survive the strict 2-of-2 rule because its 120m Development block rule failed. `drawdown_from_best_R` did not establish robust L0 specificity.

A63 therefore narrowed the current mechanism-specific early axis to **adverse-excursion depth**.

Result persistence commit: `3a8a276b31988201070c30833bd2809b45b69145`.
Scientific verdict commit: `c192ba3469a685e074c2712887212fbc4f65a69c`.

## Latest completed experiment — A64

### A64 question

**L0 EARLY MAE ECONOMIC TRANSLATION**

> Can the A62+A63 mechanism-specific `running_mae_R` deterioration be translated into one causal pre-break full-exit rule that improves untouched parent economics without sacrificing more eventual-winner PnL than it saves specifically from L0/M0, and does that exact Development-selected rule replicate OOS?

A64 was a separately preregistered economic-feasibility experiment. It did not directly convert an A62/A63 median into a trading threshold.

### Frozen candidate family

Only one feature was allowed: `running_mae_R`.

Only two decision ages were allowed:

- `60m`
- `120m`

Thresholds were learned only from eligible Development L0/M0 cases by frozen nearest-rank quantiles:

- Q25
- Q50
- Q75

The intervention architecture was deliberately simple and falsifiable:

- still live and pre-break at the fixed snapshot;
- if `running_mae_R >= threshold`, exit 100% at the decision open;
- no partial size;
- no re-entry/re-arm;
- no H05/H10 logic;
- no composite feature;
- no OOS threshold selection.

### A64 verdict

**`SOL_LONG_15UTC_L0_EARLY_MAE_ECONOMIC_TRANSLATION_A64_REJECTED_DEVELOPMENT`**

Raw 5m coverage remained **99.7671%** and all frozen parent/loss/L0/winner counts reconciled exactly.

Development threshold source:

| Age | Eligible Dev L0 | Q25 | Q50 | Q75 |
|---:|---:|---:|---:|---:|
| 60m | 33 | 0.336679R | 0.513333R | 0.737518R |
| 120m | 29 | 0.588785R | 0.664723R | 0.803653R |

All six candidates increased raw and stressed net PnL and increased raw/stressed PF, but **zero** candidates passed every frozen Development gate.

| Candidate | Raw ΔNet | 5bps ΔNet | L0 Δ | Winner Δ | Blocks raw/stress | Gate |
|---|---:|---:|---:|---:|---:|---|
| A60_Q25 | +$29.02 | +$29.02 | +$205.48 | -$215.01 | 3/6 / 3/6 | FAIL |
| A60_Q50 | +$49.99 | +$49.99 | +$117.52 | -$77.42 | 3/6 / 3/6 | FAIL |
| A60_Q75 | +$42.32 | +$42.32 | +$58.05 | -$23.17 | 3/6 / 3/6 | FAIL |
| A120_Q25 | +$86.29 | +$86.29 | +$165.54 | -$76.38 | 5/6 / 5/6 | FAIL |
| A120_Q50 | +$46.00 | +$46.00 | +$96.32 | -$49.92 | 4/6 / 4/6 | FAIL |
| A120_Q75 | +$22.57 | +$22.57 | +$45.28 | -$15.44 | 5/6 / 5/6 | FAIL |

### Decisive common failure

Every candidate failed the preregistered stressed-WR preservation requirement:

`5bps WR >= baseline 5bps WR`

Frozen Development stressed WR was approximately `40.27%`.

Candidate stressed WRs ranged from approximately `36.11%` to `39.93%`; none preserved the baseline.

The 60m candidates additionally failed block consistency (`3/6`). `A60_Q25` also failed the explicit L0-saved-greater-than-winner-damage safeguard.

### Strongest diagnostic — not a selected rule

`A120_Q25` was the strongest economic near-miss:

- age: 120m;
- threshold: `0.5887850467R`;
- 40 triggers: 22 L0, 9 other losses, 9 eventual winners;
- raw net: `$425.21` vs baseline `$338.91`;
- raw/stress ΔNet: `+$86.29`;
- raw PF: `1.388`;
- stressed PF: `1.232`;
- raw max DD: `$114.01` vs baseline `$148.06`;
- L0 ΔPnL: `+$165.54`;
- eventual-winner ΔPnL: `-$76.38`;
- positive blocks: `5/6` raw and stress;
- stressed WR: `38.77%`, below baseline.

It remains **diagnostic only**. The frozen gate cannot be relaxed after seeing this near-miss.

### OOS remained unopened

Because Development produced no fully passing candidate:

- no A64 rule was selected;
- External intervention economics were not computed;
- Reference intervention economics were not computed;
- OOS cannot be used to rescue A64.

This is the correct Development-first stopping behavior.

### A64 scientific meaning

The A62 -> A63 -> A64 chain now supports a precise distinction:

1. A62: early adverse-excursion deterioration exists.
2. A63: adverse-excursion depth is specifically associated with L0/M0 versus another never-break loss mechanism.
3. A64: static fixed-age MAE full exit contains meaningful Development economic information, but is too blunt to satisfy the full promotion objective because eventual-winner retention and stressed WR deteriorate.

Therefore:

> **Do not conclude that MAE lacks economic information. Conclude that the tested static full-exit translation is not promotable under the frozen objective.**

Result persistence commit: `ad8ecdba677ed0f96b004507535c2c3d5b78a18a`.
Scientific verdict commit: `27368e56c3966f071e54f2c79d56d56a2faa418a`.

## Closed or strongly constrained routes

Do not casually reopen:

- `A43-A44`: portfolio/week-state route;
- `A45`: pre-range filter;
- `A46`: entry/target recalibration route that failed eligibility/gates;
- `A47`: conventional pre-entry quality;
- `A47B -> A47C`: descriptive structural separator -> failed economic gate;
- `A48`: participation/volume;
- `A49`: BTC/ETH alignment for SOL;
- `A52-A53`: generic descriptive warning -> hard guard;
- `A54`: post-H05/H10 secondary trigger;
- `A55 -> A56`: terminal-near anatomy -> failed executable guard;
- `A58`: universal 1m intrabar separator;
- `A59`: H05 hybrid partial derisk/re-arm;
- `A60`: 1m range compression;
- `A61`: LOW_MFE H05 prewarning retune;
- `A62`: direct anatomy-to-intervention conversion;
- `A63`: promoting `close_H_R` or `drawdown_from_best_R` as 2-of-2 L0-specific;
- `A63`: direct MAE-specificity-to-execution conversion without a new preregistration;
- `A64`: static full-exit family at 60/120m using Development L0 Q25/Q50/Q75 MAE thresholds under the frozen A64 gate;
- `A64`: retroactively deleting/relaxing the stressed-WR gate;
- `A64`: neighboring threshold/age rescue or opening OOS for a rejected Development candidate.

## Durable lessons

1. **A47B -> A47C:** replicated structure does not imply a profitable gate.
2. **A55 -> A56:** predictive failure anatomy does not imply a profitable live exit.
3. **A59:** Development economics can reverse OOS; OOS gates remain essential.
4. **A62:** genuine early deterioration exists around 60–120m.
5. **A63:** the robust L0-specific axis narrows to `running_mae_R`.
6. **A64:** mechanism-specific information can improve PnL/PF/DD yet still fail the full promotion objective because it harms eventual-winner retention. A good diagnostic is not automatically a good decision rule.

## Current frontier

The frontier is now a **manual post-A64 winner-retention mechanism decision**.

Core question:

> What pair-native causal mechanism distinguishes MAE-deteriorating trades that still recover into eventual winners from genuine L0/M0 reference-invalidation losses, without post-hoc rescue of the rejected A64 threshold family?

This is intentionally a mechanism question before another intervention question.

`A65` is only the next available identifier. It is **not** preapproved as:

- a new MAE threshold search;
- a relaxed-WR rerun of A64;
- a partial version of A120_Q25;
- a recovery re-arm variant;
- a composite using A63-rejected features;
- an OOS look at any failed A64 candidate.

A future A65 hypothesis must be separately preregistered and should explain the winner-retention tension rather than simply optimize around the failed gate.

## Automation boundary

Automation may own reproducible plumbing:

- registry validation;
- experiment IDs and paths;
- frozen-parent/cohort/partition assertions;
- preregistration-before-implementation history checks;
- deterministic result envelopes/manifests;
- CI execution and artifact persistence.

Automation must not decide:

- the next scientific hypothesis;
- a post-hoc threshold or gate relaxation;
- which failed candidate to rescue;
- feature selection after validation inspection;
- substantive interpretation;
- scientific verdict;
- automatic state advancement.

## Update policy

Update this state only after result persistence and a separate scientific verdict. A CI run alone must never advance scientific state.
