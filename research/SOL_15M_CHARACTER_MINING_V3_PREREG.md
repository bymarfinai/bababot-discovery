# SOL 15M Character Mining V3 — Preregistration

Objective: find a causal SOLUSDT LONG character satisfying TP >=1%, RR >=1:1, >=1 executed trade/day, WR >=70%, positive expectancy after 0.15% round-trip cost, one active position.

Discovery baseline is TP +1.0% / SL -1.0% because it is the minimum allowed target and easiest valid RR>=1 configuration.

Time discipline:
- train: calendar 2023, excluding labels resolving in 2024
- development validation: calendar 2024
- reference: calendar 2025
- reference: 2026 through available data
- model is not refit after 2023 for this transfer test

Features are causal pre-entry 15m multi-horizon returns, candle geometry, ATR-normalized range/body, volatility/compression, EMA distance/slope, rolling-range location, distances to prior highs/lows, sweep-reclaim/breakout flags, plus completed 1H and 4H context.

Frozen model family: RandomForestClassifier with (max_depth,min_samples_leaf) = (4,80),(6,80),(8,80),(8,150). Threshold selection uses fixed score quantiles on 2024 only; eligible thresholds must execute >=1 trade/day. Ranking is highest WR, then net expectancy, then frequency.

Full pass requires 2024, 2025, and 2026 each to have WR >=70%, >=1 trade/day, and positive net expectancy.
