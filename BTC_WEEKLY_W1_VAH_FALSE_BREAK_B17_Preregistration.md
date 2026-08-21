# BTC Weekly W1 VAH False-Break Filter B17 — Preregistration

## Objective
Identify causal pre-entry information that separates winning from losing **direct W1 VAH breakout LONG** setups, without changing the underlying B15 setup.

## Frozen candidate universe
- BTCUSDT Binance USD-M futures.
- Active W1 VAH is computed from the most recently completed weekly 15m volume profile exactly as in B13/B15: 24 equal-width bins, base-volume POC, 70% contiguous value area.
- Level is unavailable until the source W1 period is fully completed.
- Research week cutoff: Saturday 12:00 UTC relative to Monday 00:00 UTC (`week_start + 5d12h`), matching B15/B16.
- For each complete ISO week, take only the **first** H1 candle satisfying `open <= active_W1_VAH` and `close > active_W1_VAH` before cutoff.
- LONG entry is the next H1 open.
- Exit: same-week only, fee 0.15%, favorable gross +1.15%, adverse gross -0.85%, yielding approximately net +1% / -1%. Same-H1 TP/SL ambiguity is adverse-first.
- No fallback. If no W1 VAH breakout occurs, there is no candidate that week.
- Candidate counts and baseline results must reproduce the B15/B16 W1 VAH direct-break baseline before any filter is evaluated. Material mismatch invalidates the run.

## Frozen partitions
- External untouched: 2020-01-01 through 2021-12-31 complete weeks.
- Development: 2022-01-01 through 2024-12-31 complete weeks.
- Reference validation untouched: 2025-01-01 through 2026-07-29 complete weeks.
- August 2026: diagnostic only.

## Causal feature timestamp
All features must use information fully known **before the next-H1-open entry**. 15m bars are included only when their close occurs no later than the entry timestamp; derivative metrics must be strictly prior to entry.

## Core features — always preferred
### Breakout geometry
- `break_close_above_vah_atr`
- `break_range_atr`
- `break_body_frac`
- `break_close_pos`
- `break_ret`
- `prior3h_ret`
- `prior6h_ret`
- `week_hours`

### Futures taker/volume state
For completed 15m bars in the 1h, 3h and 6h windows immediately preceding entry:
- `f_taker_imbalance_1h`, `f_taker_imbalance_3h`, `f_taker_imbalance_6h`, where imbalance = `2*taker_buy_quote/sum_quote_volume - 1`.
- `f_taker_accel_1h_vs_6h = imbalance_1h - imbalance_6h`.
- `f_qvol_rate_1h`, `f_qvol_rate_3h`: average quote-volume rate in the window divided by the average hourly quote-volume rate in the prior 7 days excluding the window.

### Spot confirmation / lead-lag
Using Binance spot BTCUSDT 15m aligned strictly by timestamp:
- `spot_ret_1h`, `spot_ret_3h`
- `spot_taker_imbalance_1h`, `spot_taker_imbalance_3h`
- `spot_minus_fut_ret_1h`, `spot_minus_fut_ret_3h`
- `spot_minus_fut_flow_1h`, `spot_minus_fut_flow_3h`
- `basis_now = futures_close/spot_close - 1`
- `basis_change_1h`, `basis_change_6h`

### Premium-index state
Using Binance futures premiumIndexKlines 15m:
- `premium_now`
- `premium_z7d`, calculated versus the strictly prior rolling 7-day mean/std.
- `premium_change_1h`, `premium_change_6h`.

## Extended derivative features
Use Binance daily futures metrics only if each partition has at least 75% feature-complete baseline-candidate coverage. Metrics are taken strictly before entry:
- `top_vs_global`
- `top_pos_chg15`
- `global_chg15`
- `metrics_taker_log`
- `oi_chg15`
- `oi_chg60`
- `oi_chg4h`

No future filling. Missing extended metrics cannot be inferred from outcome.

## Winner-vs-loser forensic table
For every feature, compute separately in development, external and reference validation:
- winner and loser medians,
- standardized mean difference (winner minus loser),
- orientation-free univariate ROC AUC `max(AUC, 1-AUC)`.

A feature is called a `stable differentiator` only when:
1. development absolute SMD >= 0.25;
2. external absolute SMD >= 0.10;
3. validation absolute SMD >= 0.10;
4. SMD sign is identical in all three partitions.

This definition is frozen before results.

## Frozen shallow filter models
Two models may be fit on development only:
1. `CORE_TREE`: all complete core features.
2. `EXTENDED_TREE`: core + derivative features, only if the 75% per-partition derivative-coverage gate is met.

Classifier is `DecisionTreeClassifier(max_depth=2, min_samples_leaf=12, class_weight='balanced', random_state=20260821)`.

For each tree, development selects one positive leaf among leaves with at least 15 development candidates. Ranking is:
1. highest Wilson lower bound of TP win rate;
2. higher win rate;
3. larger N;
4. lower numeric leaf id.

The selected model is whichever model's selected development leaf has the higher Wilson lower bound; tie-break by higher N, then CORE_TREE. That model and leaf are frozen before external/reference-validation evaluation.

## Baseline and gates
Report the unfiltered W1 VAH direct breakout baseline beside the filtered cohort.

`B17_USEFUL_FALSE_BREAK_FILTER` PASS requires on the frozen filtered cohort:
- external N >= 12 and validation N >= 10;
- external WR >= 65% and validation WR >= 65%;
- external PF > 1 and validation PF > 1;
- filtered WR strictly exceeds the corresponding unfiltered B15 baseline WR in both external and validation.

`B17_HIGH_PRECISION_FILTER` PASS requires:
- external N >= 10 and validation N >= 10;
- WR >= 80% in both external and validation;
- PF > 1 in both.

No post-result threshold, feature, model-depth, minimum-leaf, partition, target/stop or candidate-definition rescue is authorized.

## Interpretation
B17 is a **false-break confirmation experiment**, not a universal one-trade-every-week strategy. A filter may improve precision while reducing the already-limited W1-breakout coverage. Historical results do not guarantee future performance.

Live BBC must remain untouched.
