# SOL L0-L5 Loss-Taxonomy Contract

> Canonical namespace contract for the SOL residual-loss taxonomy. This document prevents the labels `L0`-`L5` from being reused as generic research-stage names.

## Scope

`L0`-`L5` are **loss-class labels**, not the Stage 0-Stage N methodology from `PAIR_NATIVE_DISCOVERY_PROTOCOL.md`.

The methodology stages and the loss taxonomy are separate namespaces.

When ambiguity is possible, use the explicit prefix `LOSS::`, for example `LOSS::L0`.

## Frozen taxonomy

| Class | Canonical meaning | Mutually exclusive classification window |
|---|---|---|
| `LOSS::L0` | Never Break + Reference Invalidation | No valid break occurs; the frozen reference-invalidation condition terminates the trade. Current state name: `NEVER_BREAK_REFERENCE_INVALIDATION`. |
| `LOSS::L1` | Never Break + Time Exit | No valid break occurs; the trade survives without structural invalidation until the frozen time/lifecycle exit. |
| `LOSS::L2` | Break then fast fail | Valid break occurs, followed by the canonical failure event within **0-5 minutes** after break. |
| `LOSS::L3` | Break then fail | Valid break occurs, followed by the canonical failure event **after 5 and within 10 minutes** after break. |
| `LOSS::L4` | Break then later fail | Valid break occurs, followed by the canonical failure event **after 10 and within 30 minutes** after break. |
| `LOSS::L5` | Break then persistent-late fail | Valid break occurs, followed by the canonical failure event **more than 30 minutes** after break. |

Historical shorthand may describe L2/L3/L4 as `fail <=5m`, `fail <=10m`, and `fail <=30m`. For an actual taxonomy table the buckets are interpreted as the non-overlapping intervals above so every classified loss has only one label.

A historical residual class `L6 = BREAK_TIME_OR_OTHER` may exist for cases outside the L0-L5 buckets. This contract does not silently force residual cases into L0-L5.

## Event-definition rule

This document freezes **taxonomy semantics**, not new price coordinates.

`valid break`, `reference invalidation`, `time exit`, and the post-break `failure event` must use the exact causal definitions frozen by the relevant parent experiment/registry. This contract must not be used to invent or retune:

- breakout thresholds;
- range length;
- session/clock;
- entry price;
- stop/invalidation coordinates;
- target;
- lifecycle.

If a future parent recalibration changes those events, it must be a separately preregistered lineage and the taxonomy mapping must be explicitly revalidated.

## Relationship to current M0/M1 mechanism identifiers

The current mature-universe state uses mechanism identifiers:

- `M0 = M0_REFERENCE_INVALIDATION`
- `M1 = M1_TIME_NO_STRUCTURAL_FAIL`

These are **mechanism/comparator identifiers**, not replacements for the loss-taxonomy namespace.

Operational correspondence under the current frozen parent:

- `LOSS::L0` is the never-break reference-invalidation cohort examined through `M0`.
- `LOSS::L1` is the never-break time/no-structural-fail cohort represented by the frozen `M1` comparator when that exact registry definition is used.

Do not mechanically relabel an M-class into an L-class unless cohort reconciliation is exact.

## Research-order contract

The established forensic order is:

1. understand `LOSS::L0` first because failure occurs before a valid breakout;
2. use `LOSS::L1` as the distinct never-break/time-survival problem rather than mixing it with structural invalidation;
3. investigate `LOSS::L2`-`LOSS::L5` as separate post-break failure timings rather than pooling all break-then-fail cases.

This ordering is a decomposition rule, **not permission to start the next experiment automatically**. `SOL_DISCOVERY_STATE.md` remains authoritative for the current frontier and next admissible scientific question.

## Output contract for research on any L-class

A class-specific investigation is not complete until its state summary records:

- **Cohort identity** — exact deterministic registry rule and N by partition.
- **Frozen parent** — range/clock/entry/target/lifecycle version used to form the cohort.
- **Question** — descriptive anatomy, mechanism specificity, intervention, economics, or another explicitly named stage.
- **Evidence** — Development plus required OOS partitions, including block stability where preregistered.
- **Conclusion** — `OPEN`, `PROVISIONAL`, `LOCKED`, `REJECTED`, or `INCONCLUSIVE`.
- **Valid scope** — what the result actually establishes.
- **Invalid scope** — what it explicitly does not establish.
- **Reopen conditions** — concrete conditions required before retesting a closed route.
- **Evidence pointers** — preregistration, result-persistence commit/artifact, and separate verdict.

No downstream layer/class may inherit raw speculative reasoning as fact. It receives only the frozen conclusion and its scope.

## Current L0 handoff

The active state through `A68` establishes a substantial `LOSS::L0/M0` forensic lineage:

- A62: replicated early-progress deterioration anatomy — supported descriptively.
- A63: `running_mae_R` survived the strict mechanism-specificity requirement versus M1 — supported.
- A64: static 60m/120m MAE full-exit translation — rejected at Development.
- A65: simple MAE-conditioned recovery anatomy — inconclusive.
- A66: fixed 50% half-reclaim sequence/hold anatomy — inconclusive.
- A67: pre-worst formation/downside-acceptance anatomy — inconclusive.
- A68: M0 as an immediate reverse-short trigger — inconclusive / unsupported as a directional short premise.

Therefore `LOSS::L0` must not be summarized as “solved into an executable exit/short rule.” The durable result is narrower: L0/M0 is a real structural long-failure cohort with replicated deterioration characteristics, while the tested intervention and reverse-short translations did not establish a robust executable edge.

## Anti-collision rule

Never create files or prose where `L0`, `L1`, ..., `L5` mean generic discovery stages unless they are explicitly prefixed with a different namespace. Prefer `Stage 0`, `Stage 1`, etc. for methodology and `LOSS::L0`-`LOSS::L5` for the SOL loss taxonomy.
