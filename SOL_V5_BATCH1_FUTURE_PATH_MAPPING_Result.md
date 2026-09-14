# SOL V5 Batch 1 — Future Path Mapping Result

- Data coverage: **99.769767%**
- OOS opportunities with complete +120m path: **139,550**
- Causal HIGH_STATE observations: **10,485**
- HIGH_STATE cutoff: prior-training 90th percentile of the frozen V4 score, applied unchanged to the following OOS year.
- Test years: 2021–2024.
- 2025+ `reference_validation` remained **CLOSED**.
- Workflow run: `34807832734`
- Artifact: `sol-v5-batch1-future-path-mapping` / ID `10333283964`
- Artifact SHA256: `e5229d371dbf8781b13464879f031053c3ad65c76714917829dd3c675dbd22a9`

## HIGH_STATE vs INACTIVE — pooled

| Metric | HIGH_STATE | INACTIVE | Lift / difference |
|---|---:|---:|---:|
| V4 60m impulse rate | 9.85% | 5.17% | **1.905x** |
| Upside diagnostic barrier hit by 120m | 32.65% | 23.11% | **1.413x** |
| UP_FIRST | 30.31% | 22.46% | **1.349x** |
| DOWN_FIRST | 29.56% | 23.63% | +5.93 pp |
| Median MFE 120m | 1.478% | 0.783% | +0.695 pp |
| Median MAE 120m | -1.392% | -0.811% | -0.580 pp |

The frozen V4 state therefore enriches future movement materially, including favorable upside geometry, but it also enriches adverse downside movement. This supports treating V4 as a **state / habitat detector**, not an immediate entry signal.

## HIGH_STATE timing

- Median time-to-MFE within the 120m observation window: **50 min**
- Median time-to-MAE within the 120m observation window: **50 min**
- Median time to the upside diagnostic impulse when hit: **45 min**
- Median adverse excursion before an eventual upside impulse hit: **-0.497%**
- Spearman(V4 score, MFE120) within HIGH_STATE: **+0.3221**
- Spearman(V4 score, MAE120) within HIGH_STATE: **-0.2945**

Higher V4 scores inside the causal HIGH_STATE are associated with both larger favorable excursion and more negative adverse excursion. The score is therefore identifying **expansion potential / activated volatility**, not direction by itself.

## HIGH_STATE timing archetypes — pooled

| Archetype | N | Rate | Median pre-up MAE | Median 120m return |
|---|---:|---:|---:|---:|
| EARLY_UP (<=30m) | 1,332 | 12.70% | -0.250% | +1.772% |
| MID_UP (35–60m) | 900 | 8.58% | -0.529% | +1.892% |
| LATE_UP (65–120m) | 1,191 | 11.36% | -0.824% | +2.124% |
| NO_UP_120 | 7,062 | 67.35% | n/a | -0.582% |

This establishes a clear activation-timing problem for Batch 2: direct entry at state detection mixes early continuation, delayed continuation after adverse excursion, late continuation, and the majority no-upside-impulse cases.

## Year stability

| Year | Active N | Up hit 120m | Inactive up hit | UP_FIRST | Inactive UP_FIRST | Median MFE120 | Median MAE120 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 3,648 | 33.28% | 23.85% | 30.04% | 23.22% | 2.404% | -2.271% |
| 2022 | 2,103 | 31.86% | 22.82% | 29.91% | 22.27% | 1.505% | -1.528% |
| 2023 | 1,865 | 36.73% | 22.17% | 34.96% | 21.52% | 1.281% | -1.093% |
| 2024 | 2,869 | 29.77% | 23.63% | 27.92% | 22.88% | 0.897% | -0.966% |

The state enrichment is present in all four OOS years, while the absolute excursion scale contracts materially over time. That is direct evidence that later TP/SL distances should be conditional/adaptive rather than fixed percentages.

## Batch 1 decision audit

- PASS — `active_n_ge_5000`
- PASS — `up_impulse120_lift_ge_1_20x`
- PASS — `up_first_lift_ge_1_20x`
- PASS — `active_up_hit_beats_inactive_ge_3_years`
- PASS — `active_up_first_beats_inactive_ge_3_years`

# BATCH 1 VERDICT: USEFUL_FOR_BATCH2

`USEFUL_FOR_BATCH2` is a characterization verdict only. It means the frozen V4 precursor state materially and repeatedly enriches future-path geometry and is suitable as the habitat in which Batch 2 searches for a causal activation/entry trigger.

It is **not** a live-trading PASS, and Batch 1 does **not** authorize TP/SL optimization. V4 remains frozen; the Batch 2 question is directional activation inside HIGH_STATE, not retuning the V4 state detector.
