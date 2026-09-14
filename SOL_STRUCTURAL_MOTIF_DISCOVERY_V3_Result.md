# SOL Structural Motif Discovery v3 — Raw 5m Walk-Forward

- Data coverage: **99.769767%**
- Raw opportunities 2020-2024: **75,085**
- Walk-forward predictions 2021-2024: **69,871**
- No ORB/VWAP/BOS/EMA/Fibonacci structure labels were inputs.
- Input motif: prior **120 minutes** of raw 5m candle path, sampled at :00 and :30.
- Unsupervised motifs per training fold: **32** MiniBatchKMeans clusters.
- Training window: rolling **2 years**.
- **2025+ remained CLOSED.**

## Overall walk-forward

| Scope | N | WR | Net PnL | Exp % | PF | Max DD | Max LS |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALL | 69,871 | 42.02% | -$44,472.03 | -0.1273% | 0.742 | $45,379.98 | 28 |
| MOTIF TRADE | 0 | n/a | $0.00 | n/a | n/a | n/a | 0 |

## Ranking diagnostic

- Spearman(predicted motif edge, realized +60m net return): **-0.0103**

| Edge quartile | N | Mean predicted edge | Realized WR | Realized Exp % | PF |
|---:|---:|---:|---:|---:|---:|
| Q1 | 17,468 | -0.1565% | 41.89% | -0.1409% | 0.713 |
| Q2 | 17,468 | -0.1409% | 42.02% | -0.1170% | 0.763 |
| Q3 | 17,467 | -0.1288% | 42.49% | -0.1182% | 0.753 |
| Q4 | 17,468 | -0.1112% | 41.69% | -0.1331% | 0.739 |

## Walk-forward diagnosis

The raw 120-minute path motifs did not contain a stable causal +60m continuation edge. The top predicted-edge quartile remained negative and did not rank realized returns monotonically. No event cleared the frozen causal MOTIF TRADE eligibility after distance/similarity blending.

Training folds occasionally contained locally positive motifs, but they did not transfer out of time. Examples:
- 2022 test fold: training motif 6 had raw train edge +0.0257%, but realized test edge was -0.1734% (N=770).
- 2022 test fold: training motif 7 had raw train edge +0.0282%, but realized test edge was -0.0957% (N=412).
- 2023 test fold: training motif 14 had raw train edge +0.0569%, but realized test edge was -0.0352% (N=262).

This points to non-stationarity rather than a hidden stable motif that was merely blocked by the trade gate.

## Frozen gate audit

- FAIL — `spearman_edge_positive`
- PASS — `q4_beats_q1_expectancy`
- FAIL — `q4_positive_expectancy`
- FAIL — `q4_pf_gt_1`
- FAIL — `trade_n_ge_100`
- FAIL — `trade_expectancy_positive`
- FAIL — `trade_pf_gt_1`
- FAIL — `trade_positive_years_ge_3`

# VERDICT: NO_ROBUST_MOTIF_SIGNAL

Do not retune K, 120-minute lookback, :00/:30 spacing, prior strength, similarity function, or gates against this same walk-forward sample. 2025+ remains unopened.