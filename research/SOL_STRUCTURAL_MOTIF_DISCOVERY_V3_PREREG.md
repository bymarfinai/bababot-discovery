# SOL Structural Motif Discovery v3 — Preregistration

## Purpose
Test whether SOL has repeatable **raw 5m price-path motifs** with causal out-of-time +60m edge, without assuming ORB, VWAP, breakout, retest, BOS, EMA, Fibonacci, RSI, or a preferred trading hour.

This is a structural discovery experiment, not TP/SL optimization.

## Closed data boundary
- Modeling/discovery universe: `2020-01-01 <= timestamp < 2025-01-01`.
- `2025+` reference/validation remains CLOSED.
- No parameter may be altered after seeing v3 walk-forward results.

## Decision opportunities
- SOLUSDT futures 5m.
- All calendar days; crypto is continuous and v3 intentionally removes the previous weekday assumption.
- Decision points occur twice per hour: bars timestamped `:00` and `:30` UTC.
- At each decision point, only the prior **24 completed 5m bars = 120 minutes** are visible.
- Entry is the **next 5m bar open**.
- Diagnostic outcome is the net return after a fixed **60-minute hold**, less **0.15% round-trip cost**.
- Reference notional: **$500**.

## Raw structural representation
For each of the 24 prior bars, v3 stores five channels derived only from information known by the decision time:
1. cumulative close path, normalized by the sequence's own 5m realized volatility;
2. candle body log-return normalized by sequence volatility;
3. high-low log-range normalized by sequence volatility;
4. close location inside the candle range;
5. log-volume relative to the sequence median.

There is **no semantic structure label** and no hour/day feature in the clustering vector.

## Unsupervised motif engine
- `MiniBatchKMeans`.
- Exactly **32 motifs** per training fold.
- Deterministic random state `42`.
- Robust feature scaling learned from the training fold only.
- Motifs are fit without using future return or win/loss labels.

## Walk-forward protocol
Test years: **2021, 2022, 2023, 2024**.

For each test year, use only the immediately preceding history, capped at a rolling **2 calendar years**:
- 2021 <- 2020
- 2022 <- 2020-2021
- 2023 <- 2021-2022
- 2024 <- 2022-2023

A training sample is eligible only if its +60m outcome was fully known before the test-year boundary.

## Motif edge estimation
Within each training fold, estimate for every motif:
- sample size;
- win rate;
- mean net +60m return;
- profit factor;
- median distance to its centroid.

Use empirical-Bayes shrinkage with prior strength **100 observations**, shrinking motif win rate and mean return toward the contemporaneous global training baseline.

For each test event:
- assign the nearest motif;
- convert centroid distance to continuous similarity using `exp(-distance / motif_median_radius)`;
- blend the motif's shrunk statistics toward the global training baseline according to that similarity.

Outputs are `pred_pwin` and `pred_edge_pct`.

## Frozen trade eligibility
A test event is marked `MOTIF TRADE` only when all are true:
- training motif N >= **100**;
- predicted net +60m edge > **0%**;
- predicted P(win) > the contemporaneous global training win rate.

No 60% WR hard threshold is used in v3. The purpose is to test whether motif-derived ranking/edge exists at all before imposing a production selectivity target.

## Frozen success audit
V3 is considered to have found a motif signal only if ALL hold out of time:
1. Spearman(predicted edge, realized net return) > 0;
2. top predicted-edge quartile has higher realized expectancy than bottom quartile;
3. top quartile has positive realized expectancy;
4. top quartile PF > 1;
5. MOTIF TRADE N >= 100;
6. MOTIF TRADE expectancy > 0;
7. MOTIF TRADE PF > 1;
8. MOTIF TRADE is profitable in at least 3 of the 4 test years.

A pass is discovery evidence only. It does not authorize opening 2025+, optimizing TP/SL, changing hold time, changing motif count, or tuning a trade threshold.

A failure rejects this frozen v3 representation as a unit. Do not tune K, 120-minute lookback, :00/:30 decision spacing, prior strength, or gates against the same walk-forward sample.