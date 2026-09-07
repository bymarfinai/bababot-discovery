# SOL LONG 15UTC Parent Pre-Range Anatomy — A45 Preregistration

## Purpose
A45 continues directly from the supported native SOL `15UTC / R360` parent selected in A20 and from the exhausted A23–A44 recovery/overlay lineage.

A44 found no replicated causal portfolio-state separator that explains the A43 portfolio rejection. A45 therefore returns to the **frozen A20 parent itself** and asks a narrower question that has not yet been tested:

> Before the 15UTC resting order is placed, does the 360-minute reference range have a causal shape/state that differs between later parent stress winners and stress failers, with the same direction in frozen OOS pools?

A45 is **anatomy only**. It is not a threshold search, parameter search, range search, clock search, target change, entry change, calendar filter, recovery change, or portfolio promotion test.

## Frozen parent
Source branch: `research/sol-long-structure-a1-run`.

Frozen source artifacts:
- `SOL_LONG_ADDITIONAL_CLOCKS_A20_TRADES.csv`
- `SOL_LONG_ADDITIONAL_CLOCKS_A20_Result.md`

Frozen cell:
- candidate: `A20_Z1_R360_H15`
- role: `CANDIDATE`
- reference: `R360`
- decision clock: `15:00 UTC`
- family: `E0_RESTING_H`
- target: `E40` / `0.40R`

Expected frozen central sample from A20:
- Development: 601 trades
- external: 281 trades
- reference_validation: 337 trades

No 03UTC/18UTC geometry, BTC geometry, or later recovery overlay is transferred into A45.

## Decision-time causality
For each frozen A20 trade, define:
- `execution_start` = 15:00 UTC decision time;
- reference start = `execution_start - 360 minutes` = 09:00 UTC;
- reference bars = the 72 completed SOLUSDT 5m candles in `[09:00, 15:00)`.

**Only those 72 completed reference candles may be used as A45 candidate features.**

A45 explicitly forbids using:
- candles at or after 15:00 UTC;
- fill delay / H1 touch timing;
- any post-fill MFE/MAE;
- parent exit path or exit reason;
- recovery path;
- final day/week portfolio outcome;
- calendar month/week identity.

This keeps every candidate feature known before the resting order is placed.

## Frozen feature set
All R-normalized features use the frozen A20 reference `R = H - L`.

### Reference positioning / directional path
1. `range_width_pct` = `R / last_reference_close`
2. `open_location_R` = `(first_reference_open - L) / R`
3. `close_location_R` = `(last_reference_close - L) / R`
4. `net_return_R` = `(last_reference_close - first_reference_open) / R`
5. `first_half_return_R` = `(mid_reference_close - first_reference_open) / R`
6. `second_half_return_R` = `(last_reference_close - mid_reference_close) / R`
7. `last60_return_R` = `(last_reference_close - close_60m_before_end) / R`
8. `last120_return_R` = `(last_reference_close - close_120m_before_end) / R`

### Path efficiency / level timing
9. `realized_close_path_R` = sum absolute 5m close-to-close moves within the reference / R
10. `signed_path_efficiency` = `(last_reference_close - first_reference_open) / realized absolute close path`
11. `high_time_fraction` = first bar index attaining reference H / 71
12. `low_time_fraction` = first bar index attaining reference L / 71
13. `high_minus_low_time_fraction` = `(first_H_index - first_L_index) / 71`

### Compression / expansion
14. `first_half_range_fraction` = first 180m high-low / full R
15. `second_half_range_fraction` = final 180m high-low / full R
16. `mean_bar_range_R` = mean 5m high-low / R
17. `last60_bar_range_ratio` = mean 5m high-low in final 60m / mean 5m high-low in preceding 300m

No additional feature may be added after outcome inspection within A45.

## Outcome
Primary outcome is frozen parent stress PnL:
- `WIN` if `pnl_5bps > 0`
- `FAIL` otherwise.

Raw outcome is retained for reconciliation/description only.

## Reconciliation gate
Before anatomy:
1. Filter A20 rows to exact frozen cell/role/ref/hour.
2. Require counts to equal the frozen A20 counts: 601 Development, 281 external, 337 reference_validation.
3. Reload the same SOLUSDT 5m source used by A1/A20.
4. For every row, recompute H, L, R from `[execution_start-360m, execution_start)` and require equality to stored A20 H/L/R within numerical tolerance.
5. Require exactly 72 complete 5m bars for every analyzed reference range.

Failure of any reconciliation condition ends A45 as `RECONCILIATION_FAIL`.

## Development-first replication rule
For each frozen feature:

1. Split Development rows by stress WIN vs FAIL.
2. Record WIN median, FAIL median, and median gap (`WIN - FAIL`).
3. Normalize absolute median gap by average WIN/FAIL IQR to obtain `effect_IQR`.
4. Repeat the gap/effect independently in each of the six frozen Development chronological blocks.
5. Open external and reference_validation only for directional replication of the already frozen feature statistics; no threshold is fitted.

A feature is `replicated_directional` only if all are true:
- Development has at least 100 WIN and 100 FAIL rows;
- Development pooled `effect_IQR >= 0.30`;
- at least 4 of 6 adequate Development blocks have a non-zero median gap with the same sign as pooled Development;
- external and reference_validation each have at least 50 WIN and 50 FAIL rows;
- external and reference_validation median gaps have the same non-zero sign as Development;
- external `effect_IQR >= 0.10`;
- reference_validation `effect_IQR >= 0.10`.

No threshold, quantile cut, conjunction, or feature combination is tested in A45.

## Fixed outputs
A45 must persist:
- `SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_TRADES.csv`
- `SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_FEATURES.csv`
- `SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_Result.md`
- `SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_Status.txt`

The result must report:
- reconciliation status and sample counts;
- frozen A20 parent stress WR/PF/net by partition;
- every replicated-directional feature and its Development / external / reference median gaps and effects;
- Development block sign stability for replicated features;
- whether evidence justifies a separately preregistered minimal guard test.

## Verdict labels
- `SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_SUPPORTED_FOR_NEXT_TEST`
- `SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_INCONCLUSIVE`
- `SOL_LONG_15UTC_PARENT_PRERANGE_ANATOMY_A45_RECONCILIATION_FAIL`

`SUPPORTED_FOR_NEXT_TEST` means only that at least one **decision-time causal range-shape feature** replicated directionally. A45 itself changes no trade and promotes no filter.

Research only. Live Baba Bot remains unchanged.
