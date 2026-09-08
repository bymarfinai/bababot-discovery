# SOL LONG 15:00 UTC L0 MAE-Conditioned Reclaim Sequence Anatomy — A66 Scientific Verdict

## Verdict

**`SOL_LONG_15UTC_L0_MAE_CONDITIONED_RECLAIM_SEQUENCE_A66_INCONCLUSIVE`**

A66 does not establish a robust reclaim-sequence feature that distinguishes genuine L0/M0 reference-invalidation losses from eventual parent winners after approximately conditioning on the adverse-excursion severity axis identified by A62-A63.

The experiment reconciled successfully, raw SOLUSDT 5m coverage remained **99.7671%**, and every fixed partition/age exceeded the preregistered matched-pair support minimum. The inconclusive verdict is therefore scientific rather than a technical, reconciliation, or support failure.

## Frozen lineage and reconciliation

The execution parent remained unchanged:

`R360 / 15UTC / E0_RESTING_H -> E40`

| Partition | Parent | CENTRAL losses | L0/M0 | Winners |
|---|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 244 |
| External Validation | 281 | 166 | 13 | 115 |
| Reference Validation | 337 | 187 | 26 | 150 |
| **Pooled** | **1,219** | **710** | **76** | **509** |

A66 did not reopen A64 intervention economics, did not rescue any A64 MAE threshold, did not combine A65 failed recovery features, and did not alter live Baba Bot.

## Why A66 existed

The preceding lineage had narrowed the problem substantially:

1. **A62:** L0/M0 develops replicated early deterioration around 60-120 minutes.
2. **A63:** `running_mae_R` is the robust L0-specific early axis among the tested A62 families.
3. **A64:** static MAE full exits contain Development economic information but fail promotion because eventual winners are damaged and stressed WR deteriorates.
4. **A65:** simple MAE-conditioned rebound magnitude, efficiency, worst timing, and post-worst slope do not robustly explain why severe-MAE winners recover while L0 fails.

A66 therefore tested a genuinely different mechanistic formulation: whether the **sequence** from worst excursion through a fixed half-reclaim and subsequent holding behavior separates recoverable winners from L0 when MAE severity is approximately matched.

## MAE-conditioned matching

| Partition | Age | Eligible L0 | Matched | Unique winner controls | Max reuse | Median abs MAE gap | P75 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Development | 60m | 33 | 33 | 20 | 5x | 0.049R | 0.166R | 0.715R |
| Development | 120m | 29 | 29 | 13 | 5x | 0.056R | 0.095R | 0.647R |
| External Validation | 60m | 12 | 12 | 9 | 2x | 0.009R | 0.026R | 0.163R |
| External Validation | 120m | 11 | 11 | 8 | 3x | 0.029R | 0.045R | 0.057R |
| Reference Validation | 60m | 22 | 22 | 17 | 3x | 0.007R | 0.024R | 0.385R |
| Reference Validation | 120m | 19 | 19 | 11 | 4x | 0.006R | 0.013R | 0.071R |

All fixed snapshot cells had full case matching. The OOS MAE match gaps were especially tight, so the lack of replication cannot reasonably be attributed to a missing control pool under the preregistered support rules.

## Preregistered sequence features

Only five families were tested around a fixed, preregistered half-reclaim level equal to 50% of the snapshot adverse excursion:

- `max_reclaim_fraction_of_mae`
- `half_reclaim_latency_fraction`
- `longest_half_reclaim_run_fraction`
- `post_half_reclaim_hold_fraction`
- `late_mae_extension_fraction`

A feature family had to satisfy Development eligibility and External + Reference replication at **both 60m and 120m**. No feature satisfied that strict 2-of-2 rule.

## Results

| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |
|---:|---|---:|---:|---:|---:|---|
| 60m | `max_reclaim_fraction_of_mae` | -0.371 / 1.094 | 3/4 | -0.418 / 1.310 | 0.000 / 0.000 | NO |
| 60m | `half_reclaim_latency_fraction` | +0.400 / 1.600 | 3/4 | +0.750 / 2.211 | 0.000 / 0.000 | NO |
| 60m | `longest_half_reclaim_run_fraction` | -0.400 / 2.267 | 3/4 | -0.553 / 4.021 | 0.000 / 0.000 | NO |
| 60m | `post_half_reclaim_hold_fraction` | -0.250 / 1.000 | 3/4 | -0.500 / 2.955 | 0.000 / 0.000 | NO |
| 60m | `late_mae_extension_fraction` | +0.208 / 0.815 | 2/4 | +0.127 / 0.407 | 0.000 / 0.000 | NO |
| 120m | `max_reclaim_fraction_of_mae` | +0.084 / 0.177 | 1/3 | -0.447 / 1.224 | -0.372 / 0.572 | NO |
| 120m | `half_reclaim_latency_fraction` | -0.100 / 0.160 | 1/3 | +0.083 / 0.195 | +0.400 / 0.667 | NO |
| 120m | `longest_half_reclaim_run_fraction` | +0.032 / 0.101 | 0/3 | -0.239 / 1.898 | -0.289 / 0.879 | NO |
| 120m | `post_half_reclaim_hold_fraction` | +0.048 / 0.158 | 1/3 | -0.250 / 1.046 | -0.333 / 0.711 | NO |
| 120m | `late_mae_extension_fraction` | +0.216 / 0.620 | 2/3 | +0.179 / 0.372 | +0.357 / 0.711 | NO |

## Why the attractive 60m pattern is not a pass

At 60m, four reclaim/hold descriptors show large Development and External effects in the preregistered direction. That pattern is descriptively interesting, but **Reference Validation shows exactly zero median gap and zero effect for those same four families**. A mechanism that disappears in the independent Reference partition cannot be promoted under the frozen rule.

Development block consistency was also `3/4`, not all four adequate blocks, for the first four 60m features. Thus even before OOS confirmation they fail the preregistered Development block criterion.

The correct action is to report this pattern, not to retune the reclaim level, remove the disagreeing block, or select only Development + External.

## Why 120m does not rescue the family

At 120m, several Development median gaps reverse the preregistered direction while External and Reference frequently point in the hypothesized direction. That instability argues against a single stable reclaim/hold mechanism across the fixed ages and partitions.

`late_mae_extension_fraction` is the most tempting near-pattern at 120m because all pooled partition gaps have the preregistered positive sign and effects of `0.620`, `0.372`, and `0.711`. It still fails Development block consistency at only `2/3`, and it also failed the block rule at 60m (`2/4`) while Reference showed zero separation there. It is therefore **not an eligible family and must not be rescued**.

No 25%/75% reclaim-level search, alternate age, relaxed block rule, reduced effect floor, or post-hoc composite is permitted after seeing A66.

## Scientific interpretation

The A62-A66 chain now supports a narrower conclusion:

> **Adverse-excursion depth remains a real L0/M0-specific early research axis, but neither the simple post-worst recovery descriptors tested in A65 nor the fixed half-reclaim sequence/hold geometry tested in A66 robustly explains why some severe-MAE trades remain recoverable winners while genuine L0/M0 proceeds to reference invalidation.**

This does not invalidate A62-A63 and does not rehabilitate A64. It says the missing winner-retention discriminator is not established by these adjacent recovery/reclaim formulations.

A66 therefore closes this exact fixed-50%-reclaim sequence family rather than inviting neighboring-parameter mining.

## Interpretation boundary

A66 does not authorize:

- rescuing `A120_Q25` or any A64 static MAE exit;
- opening A64 OOS intervention economics;
- optimizing the 50% reclaim level to 25%, 75%, or another value;
- selecting the favorable 60m Development + External pattern while ignoring Reference;
- rescuing `late_mae_extension_fraction` by relaxing the Development block rule;
- moving the fixed 60m/120m ages;
- combining A65 and A66 failed descriptors into a composite score;
- creating an exit, partial derisk, re-arm, timer, or live gate from these medians;
- modifying live Baba Bot.

## Lineage consequence

- Preserve A62 early deterioration as supported.
- Preserve A63 `running_mae_R` mechanism specificity as supported.
- Preserve A64 static MAE full-exit translation as rejected at Development.
- Preserve A65 simple MAE-conditioned recovery family as inconclusive.
- Close A66 fixed-half-reclaim sequence/hold family as **inconclusive** under the strict 2-of-2 rule.
- Keep the unresolved problem as **winner retention under severe MAE**, while no longer assuming the missing discriminator is an adjacent post-worst recovery or half-reclaim statistic.
- Any next experiment must introduce a genuinely new pair-native mechanistic question; it must not be a neighboring reclaim-level or threshold rescue.

Research only. Live Baba Bot remains unchanged.
