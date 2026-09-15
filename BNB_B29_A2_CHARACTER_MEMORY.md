# BNB B29 A2 — Character Memory / Walk-Forward Similarity Protocol

## Purpose

A2 asks one question only: **does the frozen A1 structural fingerprint retrieve historically similar BNB states whose subsequent price behaviour is stable enough to constitute a reusable character memory?**

A2 is not an entry, TP, SL, leverage, position-sizing, WR, PnL, or live-trading test. No execution rule may be created or selected here.

## Frozen input

- Symbol: `BNBUSDT`
- Representation: frozen A1 fingerprint from `research/bnb_b29_a1_structure_fingerprint.py`
- Raw loader boundary: `END = 2026-08-26 00:00:00+00:00`
- Data after that boundary is forbidden in A2.
- Decision timestamps represent fully closed 5-minute bars.

## Walk-forward folds

Exactly five chronological folds are evaluated:

1. query year 2022; memory strictly before `2022-01-01`
2. query year 2023; memory strictly before `2023-01-01`
3. query year 2024; memory strictly before `2024-01-01`
4. query year 2025; memory strictly before `2025-01-01`
5. query period 2026 through the frozen A1 boundary; memory strictly before `2026-01-01`

For a memory row to be eligible, its longest observed behaviour horizon must also be fully known before the fold start. With the maximum 360-minute behaviour horizon, `memory_ts + 360m <= fold_start` is mandatory.

No query can use earlier observations from its own evaluation fold. This is intentionally stricter than ordinary expanding-window validation.

## Query sampling

A2 does not need every 15-minute A1 row to test memory quality. To keep the test deterministic and computationally compact, queries are sampled at:

- minute `00`, and
- WIB hour divisible by 4: `00, 04, 08, 12, 16, 20 WIB`.

All eligible query rows are used; there is no outcome-based sampling.

## Similarity representation

### Numeric similarity features

The following non-redundant subset is frozen before A2 execution:

- `disp_atr_15`, `disp_atr_30`, `disp_atr_60`, `disp_atr_120`, `disp_atr_360`
- `eff_30`, `eff_60`, `eff_120`, `eff_360`
- `atr30_atr360`, `atr60_atr360`, `rv60_rv360`
- `body_range`, `close_location`
- `range_pos_60`, `range_pos_120`, `range_pos_360`
- `dist_prior_high_60_atr`, `dist_prior_low_60_atr`
- `dist_prior_high_120_atr`, `dist_prior_low_120_atr`
- `sweep_high_60`, `sweep_low_60`, `break_high_60`, `break_low_60`
- `tod_sin`, `tod_cos`

For each fold, scaling statistics are fit on memory only. Each feature is centered by the memory median and divided by memory IQR; zero/invalid IQR is replaced by 1. Scaled values are clipped to `[-8, 8]`.

### Categorical reranking features

The following A1 structural states are used only as a reranking penalty, not as exact-match filters:

- `structure_state`
- `trend_state`
- `efficiency_state`
- `vol_state`
- `range_state`
- `liquidity_state`
- `path_state`
- `wib_bucket`

This intentionally permits approximate rather than exact character matches.

## Neighbor construction

For each query:

1. Retrieve the 256 closest memory rows in scaled numeric space using Euclidean distance.
2. Add a fixed categorical mismatch penalty: `0.35 * mismatch_fraction`, where mismatch fraction is mismatched categorical states / 8.
3. Rerank the 256 candidates by adjusted distance.
4. Keep at most one analog per UTC calendar date to prevent one local episode from dominating memory.
5. Keep the first 64 unique-date analogs.
6. At least 48 analogs are required for the query to be evaluable.

The prediction weight for an analog is `1 / (1 + adjusted_distance)`. No similarity parameter is tuned in A2.

## Behaviour memory — not execution outcomes

A2 stores only close-to-close forward behaviour from the decision timestamp at fixed horizons:

- +15m
- +30m
- +60m
- +120m
- +360m

For each query/horizon, predicted behaviour is the similarity-weighted mean of the selected analog forward returns.

No entry price optimization, stop, take-profit, intrabar fill logic, fee, leverage, or PnL is allowed.

## Reported diagnostics

For each fold and pooled across folds:

- query count and evaluable query count
- memory size
- median analog count
- median adjusted analog distance and similarity score
- median same-state rates for `structure_state` and `path_state`
- Spearman correlation between predicted and realized forward returns for each fixed horizon
- sign agreement between predicted and realized forward returns for each fixed horizon

## Frozen A2 acceptance gates

A2 is `PASS` only if every integrity gate and the aggregate character-memory gate pass.

### Integrity gates

1. A1/raw coverage remains >= 99.5%.
2. No data after `2026-08-26 00:00 UTC` is touched.
3. Every selected analog timestamp is earlier than its fold start.
4. Every selected analog's +360m behaviour is fully known before its fold start.
5. Each fold has >= 20,000 eligible memory rows.
6. Each fold has >= 500 evaluable queries.
7. Median analog count is >= 48 in every fold.
8. Numeric outputs are finite.

### Structural-coherence gate

Across all evaluable queries:

- median selected-analog `structure_state` agreement >= 35%, and
- median selected-analog `path_state` agreement >= 35%.

### Aggregate character-memory gate

Let pooled Spearman rho be computed separately for all five fixed horizons.

All must hold:

- at least 4 of 5 pooled horizon rhos are > 0;
- median pooled rho across the five horizons is >= 0.03;
- mean pooled sign agreement across the five horizons is >= 50.5%;
- at least 3 of the 5 chronological folds have a positive median rho across the five horizons.

These are representation-level memory gates, not trading-performance gates.

## Stop rule

- `PASS`: A2 representation/memory is frozen and may proceed to the next B29 phase.
- `REJECT`: do not tune K, penalties, feature list, horizon list, sampling hours, thresholds, or fold definitions against these same results. Any redesign must receive a new experimental identity.
- No live orders are placed in A2.
