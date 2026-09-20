# SOL Structural Liquidity Detector V3 — Result

- 5m coverage: **99.769767%**
- Four V2 anatomy thresholds were frozen unchanged.
- 2020-2024 used only for combination construction.
- 2025 opened only after the score rule was frozen.
- 2026+ CLOSED.
- No entry, TP, SL, PnL, hour, session, indicator, or regime filter.

## Frozen construction rule

**SCORE_GE_3**

- Construction baseline: N=5,450, rate=24.81%
- Construction selected: N=318, rate=57.55%
- Construction lift: **32.74 pp**
- Construction Wilson lower: **52.06%**

## Untouched 2025 validation

- Baseline: N=1,264, structural-event rate=25.63%
- Detector selected: N=91, structural-event rate=**60.44%**
- Lift: **34.81 pp**
- Wilson 95% CI: **50.17% – 69.87%**
- BUY_SIDE: N=46, selected=58.70%, baseline=26.18%
- SELL_SIDE: N=45, selected=62.22%, baseline=25.08%

## 2025 half-year diagnostic

| Half | Baseline N | Baseline | Selected N | Selected | Lift |
|---|---:|---:|---:|---:|---:|
| 2025_H1 | 617 | 24.64% | 33 | 60.61% | 35.97 pp |
| 2025_H2 | 647 | 26.58% | 58 | 60.34% | 33.76 pp |

## Frozen validation gate audit

- PASS — selected_2025_n_ge_50
- PASS — selected_2025_rate_ge_45pct
- PASS — lift_vs_2025_baseline_ge_15pp
- PASS — wilson_lower_ge_35pct
- PASS — buy_side_above_baseline
- PASS — sell_side_above_baseline

**VERDICT: VALIDATED_STRUCTURAL_LIQUIDITY_DETECTOR**

The verdict concerns structural-liquidity classification at reclaim close only. It does not define a trade entry or economics.

2026_PLUS=CLOSED
