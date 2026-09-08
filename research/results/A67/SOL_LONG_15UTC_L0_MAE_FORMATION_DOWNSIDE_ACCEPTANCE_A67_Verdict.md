# SOL LONG 15:00 UTC L0 MAE Formation and Downside-Acceptance Anatomy — A67 Scientific Verdict

## Verdict

**`SOL_LONG_15UTC_L0_MAE_FORMATION_DOWNSIDE_ACCEPTANCE_A67_INCONCLUSIVE`**

A67 does not establish a robust pre-worst MAE-formation or completed-close downside-acceptance feature that distinguishes genuine L0/M0 reference-invalidation losses from eventual parent winners after approximately conditioning on the adverse-excursion severity axis identified by A62-A63.

The experiment reconciled successfully, raw SOLUSDT 5m coverage remained **99.7671%**, every fixed partition/age exceeded the preregistered matched-pair support minimum, the preregistration-history guard passed, and the deterministic workflow completed successfully. The inconclusive verdict is therefore scientific rather than technical, reconciliation, or support failure.

## Frozen lineage and reconciliation

The execution parent remained unchanged:

`R360 / 15UTC / E0_RESTING_H -> E40`

| Partition | Parent | CENTRAL losses | L0/M0 | Winners |
|---|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 244 |
| External Validation | 281 | 166 | 13 | 115 |
| Reference Validation | 337 | 187 | 26 | 150 |
| **Pooled** | **1,219** | **710** | **76** | **509** |

A67 did not reopen A64 intervention economics, did not resurrect A65 recovery descriptors, did not retune or recycle A66 reclaim geometry, and did not alter live Baba Bot.

## Why A67 existed

The preceding lineage had narrowed the unresolved winner-retention problem:

1. **A62:** L0/M0 develops replicated early deterioration around 60-120 minutes.
2. **A63:** `running_mae_R` is the robust L0-specific early axis among the tested A62 families.
3. **A64:** static MAE full exits contain economic information but damage eventual winners and stressed WR.
4. **A65:** simple post-worst recovery descriptors fail strict replication.
5. **A66:** fixed half-reclaim sequence/hold geometry also fails strict replication.

A67 therefore made a genuine mechanism reset. Instead of asking how price recovers after the worst excursion, it asked whether **the adverse excursion is formed differently before the first snapshot-worst bar**: persistent downside acceptance for L0 versus transient/sweep-like damage for eventual winners.

## MAE-conditioned matching

| Partition | Age | Eligible L0 | Matched | Unique winner controls | Max reuse | Median abs MAE gap | P75 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Development | 60m | 33 | 33 | 20 | 5x | 0.049R | 0.166R | 0.715R |
| Development | 120m | 29 | 29 | 13 | 5x | 0.056R | 0.095R | 0.647R |
| External Validation | 60m | 12 | 12 | 9 | 2x | 0.009R | 0.026R | 0.163R |
| External Validation | 120m | 11 | 11 | 8 | 3x | 0.029R | 0.045R | 0.057R |
| Reference Validation | 60m | 22 | 22 | 17 | 3x | 0.007R | 0.024R | 0.385R |
| Reference Validation | 120m | 19 | 19 | 11 | 4x | 0.006R | 0.013R | 0.071R |

Support and matching therefore do not explain the failed replication.

## Preregistered formation features

Only five fixed feature families were tested, all using completed bars no later than the first occurrence of the snapshot-worst low:

- `largest_mae_extension_share`
- `mae_extension_bar_fraction`
- `down_close_step_fraction`
- `close_path_efficiency_to_worst`
- `worst_bar_close_location`

A feature family had to satisfy Development eligibility and External + Reference replication at **both 60m and 120m**. No family satisfied the strict 2-of-2 rule.

## Results

| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |
|---:|---|---:|---:|---:|---:|---|
| 60m | `largest_mae_extension_share` | -0.224 / 0.592 | 2/4 | -0.231 / 0.804 | +0.057 / 0.179 | NO |
| 60m | `mae_extension_bar_fraction` | +0.048 / 0.130 | 2/4 | -0.050 / 0.116 | -0.208 / 0.677 | NO |
| 60m | `down_close_step_fraction` | +0.061 / 0.278 | 3/4 | -0.033 / 0.105 | 0.000 / 0.000 | NO |
| 60m | `close_path_efficiency_to_worst` | +0.087 / 0.228 | 2/4 | -0.069 / 0.182 | -0.151 / 0.438 | NO |
| 60m | `worst_bar_close_location` | -0.013 / 0.025 | 4/4 | +0.143 / 0.301 | -0.298 / 1.059 | NO |
| 120m | `largest_mae_extension_share` | -0.023 / 0.097 | 1/3 | -0.097 / 0.761 | +0.003 / 0.022 | NO |
| 120m | `mae_extension_bar_fraction` | +0.065 / 0.242 | 2/3 | +0.018 / 0.063 | -0.069 / 0.254 | NO |
| 120m | `down_close_step_fraction` | -0.036 / 0.215 | 1/3 | +0.030 / 0.234 | -0.030 / 0.283 | NO |
| 120m | `close_path_efficiency_to_worst` | -0.068 / 0.243 | 2/3 | +0.123 / 0.445 | -0.190 / 1.184 | NO |
| 120m | `worst_bar_close_location` | +0.176 / 0.339 | 1/3 | -0.035 / 0.133 | -0.013 / 0.053 | NO |

## Why the attractive 60m extension-concentration pattern is not a pass

`largest_mae_extension_share` at 60m is the clearest tempting pattern. Development and External both show the preregistered negative L0 gap with meaningful effects (`0.592` and `0.804`), consistent with the hypothesis that L0 damage is less dominated by one transient extension.

It still cannot be promoted. Reference Validation reverses the median-gap sign (`+0.057`) and Development block consistency is only `2/4` adequate blocks in the preregistered direction. The correct conclusion is that the 60m signal is partition-unstable, not that Reference should be ignored or that the block rule should be relaxed.

No threshold, age, sub-block, or composite rescue is permitted.

## Why worst-bar close acceptance is not a pass

`worst_bar_close_location` also fails to form a stable mechanism. At 60m Development has excellent `4/4` directional block consistency but essentially no pooled separation (`-0.013`, effect `0.025`), External reverses direction, and Reference shows a large effect in the hypothesized direction. At 120m Development itself reverses direction while both OOS partitions point weakly in the hypothesized direction.

That pattern is not coherent enough to support a single pair-native downside-acceptance mechanism across the frozen ages and partitions.

## Scientific interpretation

The A62-A67 chain now supports a narrower statement:

> **Adverse-excursion depth remains a replicated L0/M0-specific early research axis, but the unresolved winner-retention discriminator is not established by simple post-worst recovery (A65), fixed half-reclaim sequence/hold geometry (A66), or the tested pre-worst MAE-formation/completed-close downside-acceptance family (A67).**

A67 weakens the simple narrative that severe-MAE winners are merely transient sweeps while genuine L0 is a consistently more persistent grind downward, at least under the exact preregistered formation descriptors tested here.

This does not invalidate A62-A63 and does not rehabilitate A64.

## Interpretation boundary

A67 does not authorize:

- rescuing `largest_mae_extension_share` from Development + External while ignoring Reference;
- relaxing Development block consistency;
- optimizing an extension-share threshold;
- changing the 60m/120m ages after seeing the result;
- adding neighboring path-persistence or candle-acceptance metrics post hoc;
- combining A65, A66, and A67 failed descriptors into a composite score;
- reopening `A120_Q25` or any A64 static MAE exit;
- creating an exit, partial derisk, re-arm, timer, or live gate;
- modifying live Baba Bot.

## Lineage consequence

- Preserve A62 early deterioration as supported.
- Preserve A63 `running_mae_R` mechanism specificity as supported.
- Preserve A64 static MAE full-exit translation as rejected at Development.
- Preserve A65 simple MAE-conditioned recovery family as inconclusive.
- Preserve A66 fixed-half-reclaim sequence/hold family as inconclusive.
- Close A67 exact pre-worst formation/downside-acceptance family as **inconclusive** under the strict 2-of-2 rule.
- Keep the unresolved problem as **winner retention under severe MAE**.
- Any next experiment must introduce another genuinely new pair-native causal mechanism and must not merely mine neighboring formation, persistence, recovery, reclaim, or MAE-threshold variants.

Research only. Live Baba Bot remains unchanged.
