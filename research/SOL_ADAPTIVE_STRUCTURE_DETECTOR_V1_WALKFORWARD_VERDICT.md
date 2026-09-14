# SOL Adaptive Structure Detector v1 — Walk-Forward Verdict

Authoritative completed workflow run: `34803171277` (commit `d7367d101d3a95776287db9f868db66c9f6260c6`).

## Frozen protocol
- Fixed event skeleton: 15m ORB -> upside breakout -> retest -> small BOS above ORB High and anchored VWAP -> next 5m open entry.
- 60m net-return diagnostic, 0.15% roundtrip cost.
- Adaptive features are causal and known by BOS close.
- Two frozen gradient-boosted models: P(win) classifier and net-return regressor.
- Expanding walk-forward: 2020->2021, 2020-21->2022, 2020-22->2023, 2020-23->2024.
- Frozen TRADE gate: predicted P(win) >= 60% and predicted net edge >= +0.15%.
- 2025+ reference_validation remained CLOSED.

## Result
- Eligible fixed-skeleton events 2020-2024: **3,266**
- Walk-forward predictions 2021-2024: **3,084**

### All fixed-skeleton events
- WR: **41.12%**
- Net PnL: **-$1,518.37**
- Net expectancy: **-0.0985%**
- PF: **0.804**

### Frozen adaptive TRADE gate
- N: **136**
- WR: **51.47%**
- Net PnL: **-$56.11**
- Net expectancy: **-0.0825%**
- PF: **0.897**
- Max DD: **$169.29**
- Max loss streak: **4**

### Prediction quality
- ROC AUC: **0.5218**
- Brier score: **0.2492**
- Spearman(predicted edge, realized net return): **-0.0267**

Predicted-edge quartiles did not rank realized edge. The highest predicted-edge quartile had **41.66% WR**, **-0.1339% realized expectancy**, and **PF 0.772**, worse than the full event universe.

### Gated results by test year
- 2021: N=124, WR=52.42%, PnL=-$36.65, PF=0.925
- 2022: N=11, WR=45.45%, PnL=-$13.12, PF=0.761
- 2023: N=1, WR=0%, PnL=-$6.33
- 2024: N=0

## Verdict
**FAIL.**

This failure is architectural, not a threshold-selection problem. The score itself does not rank future outcomes, so the P(win)/edge gate must not be rescued by changing 0.60 or +0.15% on the same walk-forward sample.

The main implication is that the fixed aggregated ORB->retest->BOS geometry is still too generic to serve as the full SOL character representation. A future version should change the representation / detector semantics rather than optimize another decimal threshold.
