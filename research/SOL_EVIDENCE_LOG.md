# SOL Evidence Log

> Compact audit index for the SOL pair-native discovery lineage. This file is not a substitute for preregistrations, deterministic result artifacts, or scientific verdicts.

## Rules

Each evidence entry should answer only:

- what was tested;
- what evidence survived the preregistered gate;
- what did not survive;
- where the authoritative result/verdict can be audited;
- what the evidence is allowed to imply.

Do not copy full raw output into this file. Retrieve raw artifacts only for audit/debug.

## Current frozen parent

`R360 / 15UTC / E0_RESTING_H -> E40`

Mature-universe pooled counts at the A68 checkpoint:

- parent opportunities: `1,219`
- CENTRAL losses: `710`
- L0/M0: `76`
- M1: `95`
- raw winners: `509`

Partitions:

| Partition | Parent | CENTRAL losses | L0/M0 | M1 | Raw winners |
|---|---:|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 58 | 244 |
| External Validation | 281 | 166 | 13 | 16 | 115 |
| Reference Validation | 337 | 187 | 26 | 21 | 150 |

External and Reference Validation are never tuning sets.

---

## A62 — Early-progress anatomy

**Question class:** descriptive anatomy.  
**Scientific outcome:** `SUPPORTED`.

At 60m and 120m, L0/M0 showed replicated:

- deeper `running_mae_R`;
- weaker `close_H_R`;
- larger `drawdown_from_best_R`;

versus age/state-matched eventual winners.

**Allowed implication:** L0/M0 has replicated early deterioration anatomy.  
**Not allowed:** converting those descriptors directly into an executable intervention without a separate experiment.

- Result persistence: `aabdbd16514c027fe7f81fe8ecf84db589eea3da`
- Scientific verdict: `37f9c233baa0ad34c613c5fbaa67276c4cb625a3`

---

## A63 — Mechanism specificity

**Question class:** mechanism specificity versus frozen M1 never-break losses.  
**Scientific outcome:** `SUPPORTED`.

Only `running_mae_R` survived the strict 2-of-2 specificity rule at both 60m and 120m across Development and both OOS partitions.

`close_H_R` and `drawdown_from_best_R` did not survive the strict mechanism-specificity requirement.

**Allowed implication:** `running_mae_R` is the robust mechanism-specific axis identified for L0/M0 under the frozen parent.  
**Not allowed:** treating every correlated A62 descriptor as L0-specific or executable.

- Result persistence: `3a8a276b31988201070c30833bd2809b45b69145`
- Scientific verdict: `c192ba3469a685e074c2712887212fbc4f65a69c`

---

## A64 — Static MAE economic translation

**Question class:** executable/economic translation.  
**Scientific outcome:** `REJECTED AT DEVELOPMENT`.

Six preregistered static full-exit candidates crossed 60m/120m with Development L0 Q25/Q50/Q75 MAE thresholds.

All improved Development net PnL and PF diagnostically, but none preserved the frozen 5bps stressed WR baseline.

Strongest diagnostic only:

- candidate: `A120_Q25`
- Development net delta: approximately `+$86.29`
- L0 PnL delta: approximately `+$165.54`
- eventual-winner PnL damage: approximately `-$76.38`
- stressed WR: degraded

**Allowed implication:** MAE contains economic information, but the tested static full-exit family is too blunt under the frozen objective.  
**Not allowed:** OOS rescue, threshold/age retuning, gate relaxation, or promoting `A120_Q25`.

- Result persistence: `ad8ecdba677ed0f96b004507535c2c3d5b78a18a`
- Scientific verdict: `27368e56c3966f071e54f2c79d56d56a2faa418a`

---

## A65 — MAE-conditioned simple recovery anatomy

**Question class:** conditional recovery anatomy.  
**Scientific outcome:** `INCONCLUSIVE`.

Tested after matching L0/M0 cases to eventual winners on nearest `running_mae_R` severity at the same age:

- `recovery_from_worst_R`
- `recovery_efficiency`
- `bars_since_worst_fraction`
- `post_worst_close_slope_R_per_bar`

No family survived strict 2-of-2 replication.

**Allowed implication:** the tested simple post-worst recovery family does not robustly explain severe-MAE winner retention.  
**Not allowed:** post-hoc composite rescue of the same family.

- Result persistence: `e0955aad2084f1d654b2c363656d0e686583d316`
- Scientific verdict: `2d6dbef9985c075dcd5c038cdd859551f7f78e8e`

---

## A66 — MAE-conditioned fixed half-reclaim sequence anatomy

**Question class:** sequence/hold anatomy.  
**Scientific outcome:** `INCONCLUSIVE`.

A fixed 50% half-reclaim sequence/hold family failed strict 2-of-2 replication.

Observed instability:

- strong 60m Development + External patterns vanished in Reference Validation;
- 120m directions were unstable;
- Development block consistency was unstable.

**Allowed implication:** the exact fixed half-reclaim sequence family is not robust.  
**Not allowed:** reclaim-level retuning, Development+External-only rescue, or `late_mae_extension_fraction` rescue.

- Result persistence: `6f7a95bb7a44af8031fcca3d2e0196a0c48501e2`
- Scientific verdict: `5a631f61b1cff5f13dccbadfaa17ae2dcc863e9a`

---

## A67 — Pre-worst MAE formation and downside-acceptance anatomy

**Question class:** temporally earlier formation anatomy.  
**Scientific outcome:** `INCONCLUSIVE`.

Five frozen families:

- `largest_mae_extension_share`
- `mae_extension_bar_fraction`
- `down_close_step_fraction`
- `close_path_efficiency_to_worst`
- `worst_bar_close_location`

No feature passed strict 2-of-2 replication.

The tempting 60m `largest_mae_extension_share` pattern held in Development and External, then reversed in Reference and failed Development block consistency.

**Allowed implication:** the exact pre-worst formation/downside-acceptance family is not robust.  
**Not allowed:** neighboring path/candle mining to rescue the premise.

- Result persistence: `99f45ed8e8f72c236325b38858f5850066410dd0`
- Scientific verdict: `c0a0fbd5e978cc99197f99518fe630c97919b693`

---

## A68 — Post-invalidation downside-continuation anatomy

**Question class:** causal directional reset after confirmed M0 invalidation.  
**Scientific outcome:** `INCONCLUSIVE`; immediate reverse-short premise not supported.

Causal short origin was frozen as:

- invalidating 5m candle must complete first;
- earliest directional origin = `invalidation_close_ts + 5m`;
- origin price = next 5m bar open;
- same invalidation candle cannot be used as a short fill;
- primary horizons = 30m and 60m;
- 120m = persistence diagnostic only.

Integrity checks:

- raw SOLUSDT 5m coverage: `99.7671%`;
- frozen parent/loss/L0/winner reconciliation: exact in all partitions;
- causal origin matched frozen M0 parent `exit_ts`: `100%`;
- forward-data coverage: `100%` for all 76 M0 cases at 30m/60m/120m.

Primary evidence:

| Horizon | Feature | Development median / effect | Dev blocks | External median / effect | Reference median / effect | Replicated? |
|---:|---|---:|---:|---:|---:|---|
| 30m | `short_close_return_R` | -0.078R / 0.174 | 1/5 | -0.057R / 0.387 | -0.032R / 0.095 | NO |
| 30m | `short_excursion_dominance_R` | +0.012R / 0.020 | 2/5 | -0.057R / 0.258 | -0.036R / 0.095 | NO |
| 60m | `short_close_return_R` | -0.087R / 0.192 | 2/5 | -0.051R / 0.423 | +0.041R / 0.119 | NO |
| 60m | `short_excursion_dominance_R` | -0.074R / 0.108 | 2/5 | -0.154R / 0.558 | -0.041R / 0.092 | NO |

Positive values were preregistered as favorable to a short. Development block gates all failed.

120m did not rescue the premise; partition directions disagreed.

**Allowed implication:** M0 says the frozen SOL long thesis failed; it does **not** by itself establish that a robust short edge has activated.  
**Not allowed:** same-candle fill, entry-delay/horizon rescue, Reference-only 120m selection, or direct TP/SL/leverage/sizing translation.

- Result persistence: `ec01efbc0f7b75bb2fcf8453a6b1e9a035d8f878`
- Scientific verdict: `937ee518940021e899e081747f29437ca9423cad`

---

## Evidence-entry template

```text
## Axx — Title
Question class:
Scientific outcome: OPEN | PROVISIONAL | SUPPORTED | REJECTED | INCONCLUSIVE

Frozen question:
Cohort / N:
Primary evidence:
OOS / block stability:
Allowed implication:
Not allowed:

Preregistration:
Result persistence:
Scientific verdict:
```

Keep this file compact. When details become too large, link to the authoritative artifact instead of expanding the log.
