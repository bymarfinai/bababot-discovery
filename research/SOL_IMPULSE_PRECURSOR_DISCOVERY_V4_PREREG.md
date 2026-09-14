# SOL Impulse Precursor Discovery v4 — Preregistration

## Objective
Stop predicting generic 60m continuation from arbitrary structures. Instead, identify whether SOL has repeatable **pre-impulse transition characteristics** that distinguish strong upside impulses from matched false setups.

## Data boundary
- SOLUSDT 5m futures data.
- Model/discovery universe: 2020-01-01 <= timestamp < 2025-01-01.
- 2025+ reference_validation remains CLOSED.
- Decision points every 15 minutes (:00/:15/:30/:45).
- Long-side discovery only.

## Outcome and impulse definition
At each decision point, enter hypothetically at the next 5m open and observe the close 60 minutes later.
- `gross_60m_pct = exit/entry - 1`.
- `net_60m_pct = gross_60m_pct - 0.15% roundtrip cost`.
- Trailing volatility is known at signal time: standard deviation of the prior 24h 5m log returns, scaled to a 60m horizon.
- A **strong upside impulse** is defined ex ante as:
  `gross_60m_pct >= max(0.75%, 1.5 * trailing_sigma60_pct)`.

The 0.75% floor prevents tiny low-volatility moves from being called impulses; the volatility multiple makes the label regime-relative. These values are frozen before results are opened.

## Precursor window
Only information available through the decision candle is used.
- 120 minutes / 24 x 5m candles.
- Raw normalized sequence channels: close path, candle body, candle range, close location, volume.
- Transition descriptors include multi-horizon return/volatility/range, compression, directional efficiency, acceleration, volume change, location inside the prior 120m range, sweep/reclaim geometry, wick balance, and recent up-close ratio.
- Hour/day/session are **not model features**.

## Matched contrastive training
For each rolling training window, positive impulse cases are contrasted with non-impulse controls matched on:
1. same calendar month,
2. same UTC hour,
3. same trailing-volatility quintile.
Up to 3 controls per impulse are sampled deterministically. This prevents the model from winning merely by learning time-of-day or volatility regime.

## Model
Frozen `ExtraTreesClassifier`:
- 240 trees
- max_depth=8
- min_samples_leaf=30
- max_features='sqrt'
- class_weight='balanced'
- random_state=42

No hyperparameter sweep is allowed in v4.

## Walk-forward
Annual OOS tests:
- test 2021 using prior 2020,
- test 2022 using prior 2020-2021,
- test 2023 using prior 2021-2022,
- test 2024 using prior 2022-2023.
Training window is capped at two years after enough history exists.

## Diagnostics / pass gate
This run is character discovery, not final live authorization. Test-year score deciles are used only as ranking diagnostics; they are not a live threshold.

V4 passes only if all are true across 2021-2024 OOS predictions:
1. ROC AUC for impulse classification >= 0.55.
2. Top score decile has impulse-rate lift >= 1.50x versus all OOS opportunities.
3. Top score decile has positive net 60m expectancy and PF >= 1.20.
4. Top decile net PnL is positive in at least 3 of 4 test years.
5. Top score decile beats bottom score decile on both impulse rate and net expectancy.

## Stop rule
If v4 fails, do not tune impulse threshold, precursor duration, model hyperparameters, score cutoffs, or hours against the same 2021-2024 OOS sample. Any revision requires a new architecture hypothesis and preregistration.
