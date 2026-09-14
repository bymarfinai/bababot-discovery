# SOL Impulse Precursor Discovery v4 — Frozen Verdict

## Status
**FAIL — precursor signal exists, but it is not yet a tradable/stable edge.**

The frozen run completed successfully on GitHub Actions run `34806210696` from commit `d61eb72a2801ac50f6918b1f1c24651094d776a5`.

## OOS result, 2021–2024
- Raw opportunities 2020–2024: 149,902
- OOS predictions: 139,562
- Baseline strong-upside-impulse rate: 5.52%
- ROC AUC: 0.5760
- Spearman precursor score vs realized net 60m return: 0.0025
- Top score decile impulse rate: 9.46%
- Top-decile impulse lift: 1.712x
- Top score decile WR: 44.32%
- Top score decile expectancy: -0.0310%
- Top score decile net PnL: -$2,166.26
- Top score decile PF: 0.958
- Bottom score decile impulse rate: 3.65%
- Bottom score decile expectancy: -0.1597%
- Bottom score decile PF: 0.595

## Top-decile stability
- 2021: N 3,504; impulse 10.39%; WR 51.37%; expectancy +0.2128%; PnL +$3,727.92; PF 1.212
- 2022: N 3,436; impulse 8.91%; WR 43.74%; expectancy -0.1548%; PnL -$2,658.94; PF 0.833
- 2023: N 3,504; impulse 9.96%; WR 42.09%; expectancy -0.0597%; PnL -$1,045.21; PF 0.890
- 2024: N 3,513; impulse 8.57%; WR 40.08%; expectancy -0.1247%; PnL -$2,190.03; PF 0.760

## Structural diagnostic
The strongest matched-training differences before strong upside impulses were not a clean compression/reclaim motif. They were mainly **locally elevated realized movement before the impulse**:
- 15m range higher: standardized effect +0.202
- 30m range higher: +0.201
- 60m range higher: +0.199
- 60m realized volatility higher: +0.195
- 120m range higher: +0.193
- 30m realized volatility higher: +0.191
- 120m realized volatility higher: +0.184
- 15m realized volatility higher: +0.172
- distance-from-120m-high lower: -0.149
- distance-from-120m-low higher: +0.146

The model's most important features were distance from the 120m high, 120m range, 30m/60m realized volatility, 30m range, the final normalized path point, 15m/60m range, 120m return, 120m/15m realized volatility, and 120m directional efficiency.

## Interpretation
V4 is the first architecture in this SOL sequence to show a meaningful ability to rank **impulse incidence** out of sample: the top score decile contains 1.712x the baseline impulse rate and materially outperforms the bottom decile. However, the score has essentially zero monotonic relationship with realized net 60m return, and top-decile economics are negative in 3 of 4 OOS years.

Therefore the current precursor score should not be promoted to live trading and should not be threshold-tuned on the same OOS sample.

## Frozen gate audit
- PASS — AUC >= 0.55
- PASS — top-decile impulse lift >= 1.50x
- FAIL — top-decile expectancy positive
- FAIL — top-decile PF >= 1.20
- FAIL — top-decile positive years >= 3
- PASS — top beats bottom impulse rate
- PASS — top beats bottom expectancy

## Boundary
2025+ reference_validation remains CLOSED. No v4 parameter, impulse threshold, precursor duration, model hyperparameter, score cutoff, or hour selection may be retuned against the same 2021–2024 OOS sample.
