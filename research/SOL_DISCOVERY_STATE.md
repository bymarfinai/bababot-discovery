# SOL Discovery State

> Authoritative operational checkpoint for the SOL discovery lineage. Canonical preregistrations, deterministic result artifacts, and separate scientific verdict documents remain authoritative for each experiment.

## Baseline

- Pair: `SOL`
- Discovery branch: `research/sol-long-structure-a1-run`
- State originally established from commit: `12c483959af3ac87c63d671f7b2edccb2fed2218`
- Latest completed experiment: **`A68`**
- Next available experiment ID: **`A69`**
- Pair-native rule: **copy the discovery grammar, never copy the coordinates**.

`A69` is an identifier only. No A69 hypothesis, feature family, comparator, threshold, intervention, or promotion gate is pre-approved.

## Frozen execution parent

`R360 / 15UTC / E0_RESTING_H -> E40`

Do not retune range, clock, entry, or target in response to A62-A68 unless a future experiment is explicitly preregistered as a parent-recalibration lineage.

## Frozen mature universe

| Partition | Parent | CENTRAL losses | L0 / M0 | M1 | Raw winners |
|---|---:|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 58 | 244 |
| External Validation | 281 | 166 | 13 | 16 | 115 |
| Reference Validation | 337 | 187 | 26 | 21 | 150 |
| **Pooled** | **1,219** | **710** | **76** | **95** | **509** |

- `L0 = NEVER_BREAK_REFERENCE_INVALIDATION`
- Deterministic trade mechanism: `M0_REFERENCE_INVALIDATION`
- Frozen registry mechanism identifier: `M0`
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

Descriptive anatomy, mechanism specificity, economic feasibility, and production deployment remain separate stages.

## A62-A68 lineage

### A62 — Early-progress anatomy

**SUPPORTED.** At 60m and 120m, L0/M0 showed replicated deeper `running_mae_R`, weaker `close_H_R`, and larger `drawdown_from_best_R` versus age/state-matched eventual winners. A62 was descriptive only.

Result persistence: `aabdbd16514c027fe7f81fe8ecf84db589eea3da`  
Verdict: `37f9c233baa0ad34c613c5fbaa67276c4cb625a3`

### A63 — Mechanism specificity

**SUPPORTED.** Against frozen M1 never-break losses, only **`running_mae_R`** survived the strict 2-of-2 specificity rule at both 60m and 120m across Development and both OOS partitions. `close_H_R` and `drawdown_from_best_R` did not.

Result persistence: `3a8a276b31988201070c30833bd2809b45b69145`  
Verdict: `c192ba3469a685e074c2712887212fbc4f65a69c`

### A64 — Static MAE economic translation

**REJECTED AT DEVELOPMENT.** Six preregistered static full-exit candidates crossed 60m/120m with Development L0 Q25/Q50/Q75 MAE thresholds. All improved Development net PnL and PF diagnostically, but none preserved the frozen 5bps stressed WR baseline.

The strongest diagnostic, `A120_Q25`, produced approximately +$86.29 Development net delta and +$165.54 L0 PnL delta, but damaged eventual-winner PnL by about -$76.38 and reduced stressed WR. It remains diagnostic only and cannot be rescued.

Result persistence: `ad8ecdba677ed0f96b004507535c2c3d5b78a18a`  
Verdict: `27368e56c3966f071e54f2c79d56d56a2faa418a`

### A65 — MAE-conditioned simple recovery anatomy

**INCONCLUSIVE.** Four simple recovery families (`recovery_from_worst_R`, `recovery_efficiency`, `bars_since_worst_fraction`, `post_worst_close_slope_R_per_bar`) failed strict 2-of-2 replication after matching L0/M0 cases to eventual winners on nearest `running_mae_R` severity at the same age.

Result persistence: `e0955aad2084f1d654b2c363656d0e686583d316`  
Verdict: `2d6dbef9985c075dcd5c038cdd859551f7f78e8e`

### A66 — MAE-conditioned fixed half-reclaim sequence anatomy

**INCONCLUSIVE.** A fixed 50% half-reclaim sequence/hold family failed strict 2-of-2 replication. Strong 60m Development + External patterns vanished in Reference Validation; 120m directions and Development block consistency were unstable. No reclaim-level retuning or `late_mae_extension_fraction` rescue is permitted.

Result persistence: `6f7a95bb7a44af8031fcca3d2e0196a0c48501e2`  
Verdict: `5a631f61b1cff5f13dccbadfaa17ae2dcc863e9a`

### A67 — Pre-worst MAE formation and downside-acceptance anatomy

**INCONCLUSIVE.** A67 moved temporally backward and tested whether severe adverse excursion is formed differently before the first snapshot-worst bar. Five fixed families were tested:

- `largest_mae_extension_share`
- `mae_extension_bar_fraction`
- `down_close_step_fraction`
- `close_path_efficiency_to_worst`
- `worst_bar_close_location`

No feature passed strict 2-of-2 replication. The strongest tempting 60m `largest_mae_extension_share` pattern held in Development and External but reversed in Reference and failed Development block consistency. Neighboring formation/persistence mining is closed.

Result persistence: `99f45ed8e8f72c236325b38858f5850066410dd0`  
Verdict: `c0a0fbd5e978cc99197f99518fe630c97919b693`

### A68 — Post-invalidation downside-continuation anatomy

**INCONCLUSIVE.** A68 made a different causal reset. It stopped trying to predict L0 earlier and instead asked whether a **confirmed** frozen M0 reference invalidation activates an immediate reverse-short regime.

Causal short-origin semantics were frozen before implementation:

- invalidating 5m candle must first complete;
- earliest directional origin = `invalidation_close_ts + 5m`;
- origin price = open of that next 5m bar;
- same invalidation candle could not be used as a short fill;
- primary horizons = 30m and 60m;
- 120m = persistence diagnostic only.

Technical integrity was complete:

- raw SOLUSDT 5m coverage: **99.7671%**;
- frozen parent/loss/L0/winner reconciliation exact in all partitions;
- causal origin matched frozen M0 parent `exit_ts` in **100%** of cases;
- forward-data coverage = **100%** for all 76 M0 cases at 30m, 60m, and 120m.

Core primary results:

| Horizon | Feature | Development median / effect | Dev blocks | External median / effect | Reference median / effect | Full replication |
|---:|---|---:|---:|---:|---:|---|
| 30m | `short_close_return_R` | **-0.078R / 0.174** | 1/5 | **-0.057R / 0.387** | **-0.032R / 0.095** | NO |
| 30m | `short_excursion_dominance_R` | +0.012R / 0.020 | 2/5 | **-0.057R / 0.258** | **-0.036R / 0.095** | NO |
| 60m | `short_close_return_R` | **-0.087R / 0.192** | 2/5 | **-0.051R / 0.423** | +0.041R / 0.119 | NO |
| 60m | `short_excursion_dominance_R` | **-0.074R / 0.108** | 2/5 | **-0.154R / 0.558** | **-0.041R / 0.092** | NO |

Positive values were preregistered as favorable to a short. Thus Development and External `short_close_return_R` medians were actually **negative at both primary horizons**. At 60m, `short_excursion_dominance_R` was negative in Development, External, and Reference. Every Development primary block gate failed.

The frozen 120m diagnostic did not rescue the mechanism: `short_close_return_R` was -0.051R in Development, -0.195R in External, and +0.222R in Reference, while excursion dominance also disagreed across partitions.

A68 scientific meaning:

> **M0 reference invalidation is a valid statement that the frozen SOL long thesis has failed, but it is not evidence that SOL has immediately transitioned into a robust short-continuation regime. “Long invalidated” and “short edge activated” are different states.**

Therefore the simple transformation `losing long -> confirmed M0 -> immediate reverse short` is not supported under the exact causal next-bar origin and fixed 30m/60m horizons.

Result persistence: `ec01efbc0f7b75bb2fcf8453a6b1e9a035d8f878`  
Scientific verdict: `937ee518940021e899e081747f29437ca9423cad`

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
- `A66`: exact fixed-50%-half-reclaim sequence family, reclaim-level retuning, Development+External-only rescue, or `late_mae_extension_fraction` rescue;
- `A67`: exact pre-worst formation/downside-acceptance family and neighboring path/candle mining;
- `A68`: using M0 alone as an immediate reverse-short signal;
- `A68`: moving the short fill back onto the invalidation candle;
- `A68`: post-hoc short entry-delay or neighboring-horizon rescue;
- `A68`: selecting Reference 120m while ignoring Development/External disagreement;
- `A68`: direct TP/SL, leverage, sizing, or economic translation from this failed directional prerequisite.

## Durable lessons

1. Replicated anatomy is not automatically an executable rule (`A47B -> A47C`, `A55 -> A56`).
2. OOS gates are essential; Development improvement can reverse or fail robustness (`A59`, `A66`, `A67`).
3. L0/M0 has real early deterioration and `running_mae_R` is the robust mechanism-specific axis (`A62-A63`).
4. MAE contains economic information, but static full exit is too blunt under the frozen objective (`A64`).
5. Severe-MAE winner retention is not robustly explained by simple post-worst recovery (`A65`).
6. It is not robustly explained by the tested fixed half-reclaim sequence/hold family (`A66`).
7. It is not robustly explained by the tested pre-worst formation/downside-acceptance family (`A67`).
8. Confirmed structural invalidation is **not automatically an opposite-direction edge** (`A68`).
9. Repeatedly mining neighboring local price-path descriptors is scientifically weak; any next lineage needs a genuinely independent causal rationale.

## Current frontier

The frontier is now a **manual post-A68 directional reset**.

Core question:

> If frozen M0 invalidation is a valid long-thesis failure state but not an automatic short edge, what genuinely independent pair-native post-failure confirmation or standalone SOL-short structure can establish directional short expectancy without using M0 alone as the signal?

`A69` is only the next available identifier. It is **not** preapproved as:

- a TP/SL optimization of the failed A68 reverse-short premise;
- an entry-delay search after M0;
- a 120m Reference-only rescue;
- a same-invalidation-candle short;
- a neighboring horizon sweep;
- a reopened A64-A67 winner-retention route.

A subsequent short lineage must first establish either:

1. an **independent post-failure confirmation mechanism** that causally distinguishes genuine short continuation from rebound/noise after M0; or
2. a **standalone SOL-short structure** discovered pair-natively rather than treating the long failure event itself as the short setup.

Only after such a directional mechanism is supported should short economics be preregistered.

Live intervention remains prohibited.

## Automation boundary

Automation may own reproducible plumbing: registry validation, experiment paths, frozen invariant assertions, preregistration-history guards, deterministic result envelopes, CI execution, and artifact persistence.

Automation must not decide the next scientific hypothesis, rescue a failed candidate, relax a gate post hoc, select features after validation inspection, make the substantive scientific verdict, or advance state automatically.

## Update policy

Update this state only after result persistence and a separate scientific verdict. A CI run alone must never advance scientific state.
