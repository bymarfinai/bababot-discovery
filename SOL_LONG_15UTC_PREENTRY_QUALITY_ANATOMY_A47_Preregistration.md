# SOL LONG 15UTC Pre-Entry Quality Anatomy — A47 Preregistration

## Purpose
A47 continues from the frozen supported SOL LONG `15UTC / R360 / E0_RESTING_H -> E40` parent (A20/A24/A25) after A45 found no sufficiently replicated separator inside the 09:00–15:00 reference-shape feature set.

A47 asks a genuinely new question:

> Can information known before the 15:00 UTC resting order is placed identify a materially higher-quality subset of the frozen parent, especially by describing the regime before the reference range and the quality/pressure of the approach to H?

The long-run objective is a causal quality gate capable of raising parent WR toward 60% while preserving a large sample and improving PF/risk. A47 itself is anatomy only and does not alter trades.

## Frozen parent
- Market: SOLUSDT 5m, same source/partitions as A20/A45.
- Candidate: `A20_Z1_R360_H15`.
- Reference: 09:00–15:00 UTC (`R360`).
- Decision time: 15:00 UTC.
- Entry: `E0_RESTING_H`.
- Target/lifecycle: frozen `E40` A20 parent.
- Stress outcome: WIN iff frozen `pnl_5bps > 0`.
- Expected central counts: Development 601, External 281, Reference Validation 337.

A47 may not change clock, range duration, entry, target, stop/invalidation, recovery, or portfolio state.

## Causality boundary
Every A47 feature must be computable strictly from completed 5m candles before 15:00 UTC. No fill timing, post-entry candle, MFE/MAE, exit reason, recovery path, future label, calendar identity, or OOS-fitted parameter is allowed.

## New information axes
A47 deliberately does not reopen the A45 17-feature reference-shape family. It studies four new families.

### A. Pre-reference regime (strictly before 09:00 UTC)
For completed windows ending 09:00 UTC:
- `pre6_return_R`, `pre12_return_R`, `pre24_return_R`
- `pre6_range_R`, `pre12_range_R`, `pre24_range_R`
- `ref_to_pre6_range_ratio`, `ref_to_pre12_range_ratio`, `ref_to_pre24_range_ratio`
- `H_vs_pre6_high_R`, `H_vs_pre12_high_R`, `H_vs_pre24_high_R`
- `L_vs_pre6_low_R`, `L_vs_pre12_low_R`, `L_vs_pre24_low_R`

All are normalized by the frozen current reference `R` where applicable.

### B. Upper-range pressure / H freshness inside 09:00–15:00
- `close_upper70_fraction`, `close_upper80_fraction`, `close_upper90_fraction`
- `high_nearH10_fraction`, `high_nearH05_fraction`
- `close_nearH10_fraction`, `close_nearH05_fraction`
- `last_exact_H_age_min`
- `first_to_last_nearH05_span_min`
- `nearH05_after_first_H_fraction`

### C. Late compression / launch geometry
Using fixed completed windows before 15:00:
- `late30_range_R`, `late60_range_R`, `late90_range_R`
- `late30_to_prior330_range_ratio`
- `late60_to_prior300_range_ratio`
- `late90_to_prior270_range_ratio`
- `distance_to_H_R_at_15`

### D. Approach quality to H
- `approach30_efficiency`, `approach60_efficiency`, `approach120_efficiency`: signed close displacement divided by absolute close path over the fixed lookback.
- `upstep_fraction_30`, `upstep_fraction_60`, `upstep_fraction_120`: fraction of close-to-close steps > 0.
- `upper80_fraction_last30`, `upper80_fraction_last60`, `upper80_fraction_last120`.

No feature may be added after outcome inspection within A47.

## Reconciliation
Before anatomy:
1. Exact A20 frozen parent counts must match 601/281/337.
2. Current H/L/R must reconcile exactly to the 72 completed 5m bars in [09:00,15:00).
3. Every required 6h/12h/24h pre-reference window must contain complete 5m coverage at its expected boundaries.
4. A47 must enrich all 1219 parent rows or fail reconciliation.

## Development-first anatomy
For every fixed feature:
1. Compare Development stress WIN vs FAIL medians.
2. Normalize the absolute median gap by average WIN/FAIL IQR (`effect_IQR`).
3. Repeat direction independently in six frozen Development chronological blocks.
4. Only after Development statistics are frozen, inspect External and Reference Validation for directional replication.

A feature is `replicated_directional` only if all are true:
- Development >=100 WIN and >=100 FAIL observations.
- pooled Development `effect_IQR >= 0.25`.
- >=4 adequate Development blocks and >=4 same-sign blocks.
- External and Reference Validation each >=50 WIN and >=50 FAIL.
- both OOS median gaps have the same non-zero sign as Development.
- External `effect_IQR >= 0.10` and Reference Validation `effect_IQR >= 0.10`.

A feature is `strong_replicated` if, additionally:
- Development `effect_IQR >= 0.35`, and
- >=5 same-sign Development blocks.

## Authorization for next stage
A47 supports a separately preregistered A48 quality-gate test only if at least one `replicated_directional` feature exists.

A48, if authorized, must use only A47-supported features, freeze thresholds from Development only, keep E0/E40 unchanged, and report retained N/winners/losers, WR, PF, expectancy, net, max DD, max loss streak, 5bps metrics, winner-retention rate, loser-rejection rate, and OOS replication.

The aspirational WR target is >=60%, but no experiment may sacrifice economic quality or OOS discipline merely to hit that number.

## Verdicts
- `SOL_LONG_15UTC_PREENTRY_QUALITY_A47_SUPPORTED_FOR_A48`
- `SOL_LONG_15UTC_PREENTRY_QUALITY_A47_INCONCLUSIVE`
- `SOL_LONG_15UTC_PREENTRY_QUALITY_A47_RECONCILIATION_FAIL`

Research only. Live Baba Bot remains unchanged.
