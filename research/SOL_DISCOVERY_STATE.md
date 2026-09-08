# SOL Discovery State

> Authoritative operational checkpoint for the SOL discovery lineage. This file summarizes frozen state and the current scientific frontier; it does **not** replace experiment preregistrations, result artifacts, or scientific verdict documents.

## Baseline

- Pair: `SOL`
- Discovery branch: `research/sol-long-structure-a1-run`
- State originally established from commit: `12c483959af3ac87c63d671f7b2edccb2fed2218`
- Latest completed experiment: `A63`
- Next available experiment ID: `A64`
- Pair-native rule: **copy the discovery grammar, never copy the coordinates**.

`A64` is an identifier only. No A64 hypothesis, MAE threshold, snapshot, exit, derisk rule, gate, or other intervention is approved by this state update.

## Frozen execution parent

The execution parent remains frozen unless a future experiment is explicitly preregistered as a parent-recalibration lineage:

`R360 / 15UTC / E0_RESTING_H -> E40`

Do not retune range, hour, entry, or target in response to A62/A63 anatomy or specificity results.

## Frozen mature loss universe

The mature pooled CENTRAL loss universe remains fixed by the A26/A51 lineage:

| Partition | CENTRAL losses | L0 / M0 | M1 |
|---|---:|---:|---:|
| Development | 357 | 37 | 58 |
| External Validation | 166 | 13 | 16 |
| Reference Validation | 187 | 26 | 21 |
| **Pooled** | **710** | **76** | **95** |

- `L0 = NEVER_BREAK_REFERENCE_INVALIDATION`
- In the mature A51 mechanism taxonomy, L0 corresponds to the `M0_REFERENCE_INVALIDATION` mechanism used by the deterministic runners.
- `M1 = NEVER_BREAK_TIME / M1_TIME_NO_STRUCTURAL_FAIL` is the alternate never-break loss mechanism used as the frozen A63 comparator.
- External Validation and Reference Validation must never be merged into Development or used for tuning.
- Cohort identity must not be redefined from a newly observed feature.

## Scientific protocol

Every scientific experiment follows this lifecycle:

1. **Preregister** the hypothesis, cohort, causal measurements, finite feature set, support rules, and success criteria.
2. **Commit the preregistration before implementation.**
3. **Implement and run through CI** using the frozen preregistered specification.
4. **Persist deterministic result artifacts.**
5. **Write a separate scientific verdict** without post-hoc threshold rescue or retuning.
6. **Advance discovery state manually** only after the verdict is complete.

A descriptive or mechanism-specific separator is not automatically an executable trading intervention. Economic intervention requires a separate preregistered experiment.

## A62 — Early-progress anatomy

A62 asked what was already causally different in frozen L0/M0 trades relative to age/state-matched eventual winners at fixed `30m`, `60m`, and `120m` snapshots.

Verdict: **`SOL_LONG_15UTC_L0_EARLY_PROGRESS_A62_SUPPORTED`**.

The `30m` snapshot did not establish a robust family. At `60m` and `120m`, three feature families replicated across Development and both OOS partitions:

- `running_mae_R`: deeper adverse excursion;
- `close_H_R`: weaker current location relative to frozen H;
- `drawdown_from_best_R`: larger giveback from best post-entry excursion.

A62 did **not** establish `running_mfe_R`, `recovery_from_worst_R`, or `upper_half_close_fraction` as supported families.

A62 remained anatomy only; no executable threshold or intervention was authorized.

Result persistence commit: `aabdbd16514c027fe7f81fe8ecf84db589eea3da`.
Scientific verdict commit: `37f9c233baa0ad34c613c5fbaa67276c4cb625a3`.

## Latest completed experiment — A63

### A63 question

**L0 / M0 EARLY-PROGRESS SPECIFICITY**

> Is the replicated A62 60–120 minute deterioration signature actually specific to L0/M0 reference-invalidation losses, or is it also present in another never-break loss mechanism, M1_TIME_NO_STRUCTURAL_FAIL?

A63 was descriptive/mechanistic specificity only. It did not test trading economics.

The comparator was frozen before result inspection:

- Case: exact frozen `M0_REFERENCE_INVALIDATION` losses.
- Control: exact frozen `M1_TIME_NO_STRUCTURAL_FAIL` losses.
- Same partition.
- Development additionally required the same frozen `dev_block`, with no relaxation.
- Both case and control had to remain live and pre-break at the same fixed age.
- Only the three A62-supported feature families were carried forward.
- Only the two A62-supported ages, `60m` and `120m`, were carried forward.

A63 therefore did not reopen unsupported A62 features or create a new feature/age sweep.

### A63 verdict

**`SOL_LONG_15UTC_L0_EARLY_PROGRESS_SPECIFICITY_A63_SUPPORTED`**

Reconciliation remained exact:

| Partition | Parent trades | CENTRAL losses | L0 / M0 | M1 |
|---|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 58 |
| External Validation | 281 | 166 | 13 | 16 |
| Reference Validation | 337 | 187 | 26 | 21 |
| **Pooled** | **1,219** | **710** | **76** | **95** |

Raw SOLUSDT 5m coverage was **99.7671%**.

### A63 matching support

| Partition | Age | Eligible L0 | Matched M1 | Unique M1 controls | Max reuse |
|---|---:|---:|---:|---:|---:|
| Development | 60m | 33 | 33 | 24 | 2x |
| Development | 120m | 29 | 29 | 22 | 2x |
| External Validation | 60m | 12 | 12 | 9 | 2x |
| External Validation | 120m | 11 | 11 | 8 | 2x |
| Reference Validation | 60m | 22 | 22 | 13 | 3x |
| Reference Validation | 120m | 19 | 19 | 11 | 2x |

All fixed snapshots met the preregistered support minimums.

### What A63 established

Only **`running_mae_R`** passed the strict 2-of-2 L0-specificity rule.

#### `running_mae_R` — L0-specific at both 60m and 120m

At `60m`:

- Development: L0-minus-M1 median gap `+0.222R`, effect `1.219`, Development block direction `4/4`.
- External Validation: `+0.114R`, effect `0.545`.
- Reference Validation: `+0.320R`, effect `0.798`.

At `120m`:

- Development: `+0.216R`, effect `1.235`, Development block direction `3/3`.
- External Validation: `+0.206R`, effect `0.969`.
- Reference Validation: `+0.240R`, effect `0.655`.

The same preregistered direction therefore survives Development and both OOS partitions at **both fixed ages**.

The narrow supported statement is:

> L0/M0 reference-invalidation losses experience systematically deeper early adverse excursion than another never-break loss mechanism by 60 minutes, and that mechanism-specific difference remains visible at 120 minutes.

### What A63 did not establish

#### `close_H_R`

`close_H_R` fully replicated at `60m`, but at `120m` its Development block-direction rule was only `2/3`. It therefore failed the strict 2-of-2 family-specificity criterion.

It must not be rescued by changing the block rule, age, threshold, or comparator after seeing the result.

#### `drawdown_from_best_R`

`drawdown_from_best_R` did not fully replicate as L0-specific at either fixed age. Its A62 separation versus eventual winners therefore does not survive as a robust L0-versus-M1 mechanism-specific family.

It must not be rescued by a post-hoc composite or alternate threshold within the A63 lineage.

### A63 interpretation boundary

A63 remains **mechanism specificity, not execution**.

The observed MAE gaps and medians are not thresholds. A63 does not authorize:

- an MAE stop threshold;
- emergency exit;
- partial derisking;
- position-size reduction;
- entry filtering;
- composite loser score;
- stop-loss modification;
- any live Baba Bot change.

A future economic-feasibility experiment is now scientifically justified because A62 established early separation and A63 established mechanism specificity. But that future experiment must be separately preregistered and must explicitly quantify:

- losses saved;
- future-winner damage;
- non-L0 trade damage;
- total PnL impact;
- drawdown impact;
- trade retention / participation impact;
- Development block consistency;
- External and Reference Validation economics.

Result persistence commit: `3a8a276b31988201070c30833bd2809b45b69145`.
Scientific verdict commit: `c192ba3469a685e074c2712887212fbc4f65a69c`.

## Closed or strongly constrained routes

The following lineage history should not be reopened casually:

- `A43-A44`: portfolio/week-state path closed.
- `A45`: pre-range filter route did not produce a robust filter.
- `A46`: native entry/target recalibration candidates failed eligibility/gates.
- `A47`: conventional pre-entry quality route did not replicate.
- `A47B -> A47C`: replicated structure did not translate into a profitable gate.
- `A48`: participation/volume route produced no actionable replicated separator.
- `A49`: BTC/ETH market-alignment route produced no replicated SOL separator.
- `A50-A51`: mature loss taxonomy became mechanistic; terminal loss is not itself a mechanism.
- `A52-A53`: descriptive failure warnings did not imply deployable guards.
- `A54`: post-H05/H10 secondary trigger was not robust OOS.
- `A55 -> A56`: strong failure anatomy did not translate into a profitable live exit.
- `A57`: confirmation differs by mechanism; a universal sequence is suspect.
- `A58`: 1-minute intrabar decomposition produced no robust universal separator.
- `A59`: H05 hybrid/partial derisk was not robust across OOS partitions.
- `A60`: 1-minute range-compression route did not replicate robustly.
- `A61`: LOW_MFE H05 pre-warning closed as inconclusive/failed; no threshold/window retuning.
- `A62`: direct anatomy-to-intervention conversion is prohibited.
- `A63`: only `running_mae_R` is established as 2-of-2 L0-specific versus M1. `close_H_R` and `drawdown_from_best_R` must not be promoted as independently established L0-specific mechanisms.
- `A63`: direct MAE-specificity-to-intervention conversion is also prohibited without a new preregistered economic test.

## Durable lessons

Four lineage lessons now define the operating discipline:

1. **A47B -> A47C:** replicated structure does not imply a profitable gate.
2. **A55 -> A56:** predictive failure anatomy does not imply a profitable executable exit.
3. **A62:** genuine early deterioration exists by roughly 60–120 minutes.
4. **A63:** after controlling against another never-break loss mechanism, the robust early L0-specific axis narrows to **adverse-excursion depth (`running_mae_R`)**.

Accordingly, cohort identity, descriptive anatomy, mechanism specificity, and executable economics remain separate scientific stages.

## Current frontier

The current frontier is a **manual post-A63 economic-translation decision**.

Core question:

> Can the A62+A63 mechanism-specific `running_mae_R` deterioration be translated into a causal economic intervention without destroying future winners, non-L0 trades, total PnL, or OOS robustness?

This is now a scientifically justified next stage, but **not a preapproved A64 experiment**.

`A64` remains merely the next available identifier. Before implementation, a separate A64 preregistration would need to freeze, at minimum:

- the exact economic intervention family to test;
- how any MAE decision boundary is obtained without OOS tuning or post-hoc rescue;
- fixed decision age(s);
- treatment of trades that already exited before the decision point;
- comparator/base economics;
- winner-damage accounting;
- non-L0 damage accounting;
- Development support and block gates;
- External and Reference Validation economic gates;
- no threshold search after validation inspection.

No threshold should be inferred directly from the A63 median gaps or effects.

## Automation boundary

Automation may own reproducible plumbing:

- registry validation;
- experiment IDs and paths;
- frozen-parent/cohort/partition assertions;
- preregistration-before-implementation history checks;
- deterministic result envelopes/manifests;
- CI execution and artifact persistence.

Automation must **not** decide:

- the next scientific hypothesis;
- a post-hoc MAE threshold;
- which features to mine after seeing validation data;
- whether a failed lineage should be rescued;
- the substantive meaning of a result;
- the final scientific verdict;
- automatic advancement to the next experiment.

## Update policy

Update this state only after the corresponding experiment result has been persisted and a scientific verdict has been made. A CI run alone must never advance the scientific state.
