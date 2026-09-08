# SOL LONG 15:00 UTC L0 Early Progress Anatomy — A62 Scientific Verdict

## Verdict

**SOL_LONG_15UTC_L0_EARLY_PROGRESS_A62_SUPPORTED — descriptive/mechanistic only.**

A62 successfully reconciled the frozen SOL parent and mature loss taxonomy and found a replicated early-progress difference for L0/M0 trades that is already visible well before terminal-near failure anatomy.

This verdict does **not** authorize an exit, derisk rule, entry filter, threshold, composite score, or live Baba Bot change.

## Provenance

- Frozen execution parent: `R360 / 15UTC / E0_RESTING_H -> E40`
- A62 preregistration add commit: `5486e988aea5fe913d16af96aea43335eb4dff7e`
- Pre-implementation causal timing amendment: `c61ae813b860088047f7a43837d4f9e6196503fb`
- A62 implementation add commit: `d568e1bf6ed9ab10af09ed2333fd901d97c34fbc`
- Successful scientific run SHA: `ed6b1597c8a23f44184c60d92d7e44d90d5437dc`
- Result persistence commit: `aabdbd16514c027fe7f81fe8ecf84db589eea3da`
- Raw SOLUSDT 5m coverage: `99.7671%`

The E0 H-touch/fill candle was excluded from path features because fill occurs intrabar and the frozen simulator begins evaluation on the next candle. No A62 feature uses the potentially pre-fill portion of the entry candle.

## Frozen-universe reconciliation

| Partition | Parent trades | CENTRAL losses | L0 / M0 |
|---|---:|---:|---:|
| Development | 601 | 357 | 37 |
| External Validation | 281 | 166 | 13 |
| Reference Validation | 337 | 187 | 26 |
| **Pooled** | **1,219** | **710** | **76** |

The mature `L0 = NEVER_BREAK_REFERENCE_INVALIDATION` / `M0` identity was not redefined from A62 features.

## What replicated

A feature family had to pass the preregistered Development gate and replicate in both External Validation and Reference Validation at at least **2 of the 3 fixed snapshots** (`30m`, `60m`, `120m`).

Three families passed:

### 1. `running_mae_R` — SUPPORTED

L0/M0 trades developed **deeper adverse excursion** than age/state-matched eventual winners.

- 60m: Dev gap/effect `+0.260R / 0.990`; External `+0.135R / 0.523`; Reference `+0.216R / 0.768`.
- 120m: Dev `+0.345R / 1.560`; External `+0.232R / 0.829`; Reference `+0.360R / 1.484`.
- Development block direction: `4/4` adequate blocks at 60m and `3/3` at 120m.

### 2. `close_H_R` — SUPPORTED

By 60–120 minutes, L0/M0 trades were **materially lower relative to the frozen reference high H** than matched eventual winners.

- 60m: Dev gap/effect `-0.353R / 1.231`; External `-0.318R / 1.354`; Reference `-0.250R / 1.302`.
- 120m: Dev `-0.377R / 1.419`; External `-0.350R / 1.870`; Reference `-0.290R / 0.915`.
- Development block direction: `4/4` at 60m and `3/3` at 120m.

### 3. `drawdown_from_best_R` — SUPPORTED

L0/M0 trades showed **larger giveback from their best post-entry excursion** than matched eventual winners.

- 60m: Dev gap/effect `+0.279R / 1.585`; External `+0.164R / 1.091`; Reference `+0.076R / 0.304`.
- 120m: Dev `+0.218R / 0.841`; External `+0.223R / 1.109`; Reference `+0.243R / 0.888`.
- Development block direction: `4/4` at 60m and `3/3` at 120m.

## What did not replicate as a family

- `running_mfe_R`: full replication only at 120m, so it failed the frozen 2-of-3 family rule.
- `recovery_from_worst_R`: no fixed snapshot achieved full replication.
- `upper_half_close_fraction`: no fixed snapshot achieved full replication.

Accordingly, A62 does **not** support a broad claim that L0/M0 is simply identifiable by low early MFE, weak recovery-from-worst, or low upper-half occupancy.

## Timing interpretation

The 30-minute snapshot did not produce a fully replicated family. The robust pattern emerges at **60 minutes** and persists at **120 minutes**.

The supported anatomy is therefore narrower and more useful than a generic “slow winner versus fast loser” story:

> L0/M0 trades become distinguishable by a combination of deeper adverse path, a substantially weaker current location relative to H, and larger giveback from the best excursion. The evidence becomes robust around the 60-minute age rather than immediately after entry.

This is an anatomy statement, not an intervention rule. In particular, the observed 60m/120m medians are **not thresholds** and must not be converted post hoc into a stop, derisk rule, or classifier.

## Scientific consequence

A62 establishes that the genuine never-break/reference-invalidation mechanism has a replicated **early path deterioration signature** before the later terminal-confirmation anatomy studied in A55.

It also preserves the key lesson from A55 -> A56: being able to recognize a future-loser anatomy does not imply that acting on it improves trading economics. Any economic intervention must be a new preregistered experiment with its own winner-damage accounting and OOS gates.

## Lineage decision

A62 is complete and supported as a descriptive/mechanistic experiment.

The next experiment identifier may advance to `A63`, but **no A63 hypothesis is automatically approved by this verdict**. The next scientific question must be chosen manually from the A62 result rather than generated by threshold rescue, feature mining, or direct conversion into a live guard.

Research only. Live Baba Bot remains unchanged.
