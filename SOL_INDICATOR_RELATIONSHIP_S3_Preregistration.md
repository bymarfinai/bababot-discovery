# SOL Indicator Relationship Discovery — Stage 3 Preregistration

**Status:** FROZEN BEFORE STAGE 3 RESULT OBSERVATION  
**Parent:** Stage 2 target definition is frozen and unchanged.  
**Pair:** SOLUSDT USD-M perpetual  
**Live trading:** untouched.

## Objective

Stage 3 asks two descriptive/predictive questions without building a multi-indicator trading rule.

### Stage 3A — single-indicator relationship discovery
For each candidate indicator independently, does its causally-known value at decision time change:
- probability that +1% is touched before -1% within 4h;
- probability that -1% is touched before +1% within 4h;
- 4h forward return;
- 4h MFE / MAE?

### Stage 3B — 5m price impulse -> future expansion
After a completed 5m SOL move of a given magnitude, does price tend to:
- continue in the same direction;
- reach additional +X% / -X% expansion;
- reverse by 1%;
- show diminishing continuation / exhaustion as the initial 5m impulse gets larger?

Stage 3B is an event-study diagnostic. It does not replace the Stage 2 primary 15m decision grid.

## Frozen partitions

- Development: 2023-01-01 <= t < 2025-01-01
- Validation 2025: 2025-01-01 <= t < 2026-01-01
- Validation 2026: 2026-01-01 <= t < frozen data end

No threshold may be learned from validation.

## Stage 3A decision clock / target

- Decision grid: every 15m, as frozen in Stage 2.
- Entry anchor: first raw 5m open at decision time after the completed 15m bar.
- Primary target: `target_1pct_4h`.
- Secondary descriptive outcomes: 1h/2h/8h first-touch, 1h/2h/4h/8h forward return, MFE/MAE.
- Same-5m +1%/-1% ambiguity: never credited as a directional win.

## Stage 3A frozen feature set

All features are computed causally from observations available at or before decision time.

### Volume
1. `quotevol_15m` — completed 15m quote volume.
2. `quotevol_ratio_1h` — current completed 15m quote volume / mean of prior four completed 15m bars.
3. `quotevol_z_24h` — current 15m quote volume z-score versus prior 96 completed 15m bars.
4. `trades_ratio_1h` — current completed 15m trade count / mean prior four completed 15m bars.

### Taker / aggressive flow
5. `taker_buy_ratio_15m` — sum taker-buy quote / sum quote volume in completed 15m.
6. `taker_imb_15m` — 2*taker_buy_ratio - 1.
7. `taker_imb_1h` — quote-volume-weighted imbalance over prior four completed 15m bars.
8. `taker_imb_change_1h` — current 15m imbalance minus prior-four-bar weighted imbalance.

### Breakout / location
9. `loc_24h` — completed 15m close location in prior completed 24h high-low range.
10. `dist_high_24h` — close / prior-24h-high - 1.
11. `dist_low_24h` — close / prior-24h-low - 1.
12. `breakout_up_24h` — max(0, close/prior-24h-high - 1).
13. `breakout_down_24h` — max(0, prior-24h-low/close - 1).

### Open interest
Source: official Binance USD-M daily metrics archives, latest completed observation at or before decision time. Never forward-nearest align.
14. `oi_value`
15. `oi_chg_15m`
16. `oi_chg_1h`
17. `oi_chg_4h`

### Funding
Source: official Binance funding history, only fundingTime <= decision time.
18. `funding_rate`
19. `funding_z_30` — z-score over prior 30 published funding observations.
20. `funding_change` — current published funding rate minus previous published rate.

## Frozen single-indicator analysis

For each continuous feature:
- determine Development quintile cut points (20/40/60/80%);
- freeze those cut points;
- apply the exact same boundaries to 2025 and 2026;
- report per partition and bucket:
  - N;
  - LONG / SHORT / NONE / AMBIGUOUS counts;
  - LONG first-touch rate;
  - SHORT first-touch rate;
  - median 4h forward return;
  - median max-up 4h;
  - median max-down 4h.

For binary breakout magnitude fields with a large zero mass:
- keep a ZERO bucket;
- non-zero Development observations are split into LOW / MID / HIGH tertiles;
- validation uses frozen Development thresholds.

Also report:
- top-minus-bottom LONG-rate lift;
- top-minus-bottom SHORT-rate lift;
- Spearman-style rank correlation between ordered bucket and median 4h forward return;
- direction consistency across Development, 2025, and 2026.

Stage 3A is descriptive. No feature becomes a trading filter in Stage 3.

### Frozen replication classification

For each feature define directional score per bucket as:
`D = LONG first-touch rate - SHORT first-touch rate`.

Compare highest bucket versus lowest bucket:
`delta_D = D_high - D_low`.

A feature is:
- `REPLICATED_DIRECTIONAL` only if endpoint buckets have N >=200 each in Development and N >=100 each in both validation partitions, `abs(delta_D_dev) >= 0.05`, both validation `delta_D` values have the same sign as Development, and each validation has `abs(delta_D) >= 0.02`.
- `NON_INFORMATIVE` if `abs(delta_D) < 0.02` in Development, 2025, and 2026.
- otherwise `UNSTABLE_OR_WEAK`.

This classification is frozen before result execution and is not a promotion rule.

## Stage 3B — frozen 5m impulse definitions

Event clock: every completed raw 5m bar.  
Impulse return:
`impulse_ret_5m = close/open - 1`.

Direction-specific thresholds are frozen before result observation:

- 0.50%
- 0.75%
- 1.00%
- 1.50%
- 2.00%
- 3.00%

For UP threshold `p`: event if `impulse_ret_5m >= p`.  
For DOWN threshold `p`: event if `impulse_ret_5m <= -p`.

Entry anchor for Stage 3B:
- next raw 5m open after the impulse bar completes.

No event deduplication in the anatomy table. A separate de-overlapped sensitivity table keeps only the first qualifying event until 4h has elapsed; this is descriptive only.

### Future expansion measurements

For each impulse event, measure same-direction expansion from the next-open anchor over:
- 1h
- 2h
- 4h
- 8h

Frozen continuation thresholds:
- +0.50% additional expansion
- +1.00%
- +2.00%
- +3.00%

For DOWN events use symmetric negative expansion.

Report:
- N;
- probability of each additional expansion threshold by horizon;
- median and p75 same-direction MFE;
- median opposite-direction adverse excursion;
- probability of opposite-direction 1% reversal within 4h;
- median time to additional 1% expansion when reached.

This explicitly tests whether a larger initial 5m impulse predicts larger continuation or instead increasing exhaustion/reversal.

## Missing data

- OHLCV/taker rows require exact raw coverage.
- OI rows are analyzed only where official metrics observations exist and are causally alignable.
- Funding rows are analyzed only where a published funding observation exists.
- Missing OI/funding never causes OHLCV/taker rows to be dropped from their own feature analyses.
- Every feature reports effective coverage and date range.

## Robustness / anti-overfitting

1. Stage 2 target remains frozen.
2. Feature definitions above are frozen before results.
3. No threshold sweep in Stage 3A.
4. Stage 3B impulse and expansion thresholds above are frozen.
5. Validation data may confirm/reject a relationship but cannot redefine buckets.
6. Overlapping observations are anatomy, not independent statistical trials.
7. Final executable trade economics remain Stage 7/8 work.

## Stage 3 completion

Stage 3 completes only after deterministic result artifacts exist for:
- 3A feature coverage;
- 3A frozen-bucket relationship tables;
- 3A cross-partition summary;
- 3B impulse-expansion mapping;
- 3B de-overlapped sensitivity;
- a scientific verdict separating robust, unstable, and non-informative single-variable relationships.

No Stage 4 interaction rule is authorized until Stage 3 is persisted.

**Preregistered status: STAGE3_FROZEN_BEFORE_RESULTS**
