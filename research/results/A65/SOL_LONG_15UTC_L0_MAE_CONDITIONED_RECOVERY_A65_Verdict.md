# SOL LONG 15:00 UTC L0 MAE-Conditioned Winner Recovery Anatomy — A65 Scientific Verdict

## Verdict

**`SOL_LONG_15UTC_L0_MAE_CONDITIONED_RECOVERY_A65_INCONCLUSIVE`**

A65 does not establish a robust recovery-path feature that distinguishes genuine L0/M0 reference-invalidation losses from eventual parent winners after approximately conditioning on the adverse-excursion severity axis identified by A62-A63.

The experiment reconciled successfully and had sufficient matched-pair support at both fixed ages in all three partitions. The inconclusive verdict is therefore scientific, not a technical or data-support failure.

## Frozen lineage and reconciliation

The execution parent remained unchanged:

`R360 / 15UTC / E0_RESTING_H -> E40`

The parent universe reconciled exactly:

| Partition | Parent | CENTRAL losses | L0/M0 | Winners |
|---|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 244 |
| External Validation | 281 | 166 | 13 | 115 |
| Reference Validation | 337 | 187 | 26 | 150 |
| **Pooled** | **1,219** | **710** | **76** | **509** |

Raw SOLUSDT 5m coverage remained **99.7671%**.

A65 did not reopen A64 intervention economics, did not reuse A64 Q25/Q50/Q75 thresholds as a gate, and did not alter live Baba Bot.

## Why A65 existed

The prior lineage established three separate facts:

1. **A62:** L0/M0 shows replicated early-path deterioration by roughly 60-120 minutes.
2. **A63:** `running_mae_R` is the only tested A62 family that remained specifically L0/M0 versus M1 at both 60m and 120m.
3. **A64:** static full exit on Development-derived MAE thresholds improved several Development economics diagnostics but failed the complete promotion gate because eventual winners were damaged and stressed WR deteriorated.

A65 therefore asked a narrower mechanism question before any further intervention:

> Holding early MAE severity approximately constant, do eventual winners exhibit a distinct recovery path that L0/M0 fails to exhibit?

## MAE-conditioned matching

Each eligible L0/M0 case was matched to an eventual parent winner at the same fixed age and partition, with Development additionally constrained to the same frozen `dev_block`. The chosen control minimized absolute `running_mae_R` distance. Control reuse was preregistered and reported.

| Partition | Age | Eligible L0 | Matched | Unique winner controls | Max reuse | Median abs MAE gap |
|---|---:|---:|---:|---:|---:|---:|
| Development | 60m | 33 | 33 | 20 | 5x | 0.049R |
| Development | 120m | 29 | 29 | 13 | 5x | 0.056R |
| External Validation | 60m | 12 | 12 | 9 | 2x | 0.009R |
| External Validation | 120m | 11 | 11 | 8 | 3x | 0.029R |
| Reference Validation | 60m | 22 | 22 | 17 | 3x | 0.007R |
| Reference Validation | 120m | 19 | 19 | 11 | 4x | 0.006R |

Thus every preregistered snapshot exceeded the minimum matched-pair support rule. A65 cannot be dismissed as simply underpowered by the frozen support criteria.

## Preregistered recovery features

Only four finite feature families were tested:

- `recovery_from_worst_R`
- `recovery_efficiency`
- `bars_since_worst_fraction`
- `post_worst_close_slope_R_per_bar`

The frozen hypothesis predicted lower values for L0/M0 than for MAE-matched eventual winners.

A feature family required full Development eligibility plus External and Reference replication at **both 60m and 120m**. No feature satisfied this strict 2-of-2 rule.

## Results

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

### Why this is not a near-pass

At 60m, some features show descriptive separation, but Development block consistency is insufficient and Reference Validation is weak or reverses direction for several families.

At 120m, three of the four Development median gaps (`recovery_from_worst_R`, `recovery_efficiency`, and `bars_since_worst_fraction`) reverse the preregistered direction even though External and Reference often point in the hypothesized direction. That cross-partition inconsistency is substantive evidence against a stable simple recovery mechanism.

`post_worst_close_slope_R_per_bar` is directionally negative across all partitions at 120m, but its Development effect is only `0.254`, below the frozen `0.30` gate, and its Development block rule is only `2/3`. It therefore also fails without rescue.

No threshold, age, support rule, direction, effect floor, or block criterion may be altered after observing these results.

## Scientific interpretation

The A62-A65 chain now supports a more constrained conclusion:

> **Adverse-excursion depth is a replicated L0/M0-specific research axis, but among the preregistered simple post-worst recovery descriptors, A65 did not find a stable additional mechanism that explains why some MAE-deteriorating trades still become winners while genuine L0/M0 fails.**

This matters because it prevents an attractive but unsupported story: A64's winner damage cannot presently be explained by saying that winners simply “rebound better after the worst excursion” according to these four fixed descriptors.

A65 does **not** invalidate A62 or A63. It also does **not** rehabilitate A64. Instead it closes this exact simple MAE-conditioned recovery-feature family as an explanation under the frozen A65 design.

## Interpretation boundary

A65 does not authorize:

- rescuing any A64 static full-exit candidate;
- reopening OOS intervention economics for A64;
- converting any A65 median into a live threshold;
- selecting only the favorable 60m feature results;
- selecting only favorable OOS results when Development failed;
- retuning the 120m feature definitions because Development reversed direction;
- lowering the Development effect threshold for `post_worst_close_slope_R_per_bar`;
- combining the four failed families into a composite score post hoc;
- adding `close_H_R` or `drawdown_from_best_R` back into the lineage as if A63 had supported them 2-of-2;
- modifying live Baba Bot.

## Lineage consequence

- Preserve A62 early-progress anatomy as supported.
- Preserve A63 `running_mae_R` mechanism specificity as supported.
- Preserve A64 static MAE full-exit family as rejected at Development; no threshold rescue.
- Close A65's exact MAE-conditioned simple recovery feature family as **inconclusive** under its strict 2-of-2 rule.
- Keep the central unresolved problem as **winner retention under severe MAE**, but do not assume the missing discriminator is a simple post-worst rebound statistic.
- Any next experiment must introduce a genuinely new, preregistered pair-native mechanistic question rather than recombining failed A65 features or relaxing A64 gates.

Research only. Live Baba Bot remains unchanged.
