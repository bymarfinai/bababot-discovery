# BNB 01:00 WIB Post-Leave Sequence Diagnosis — B27FM

- Raw loader coverage: 100.0000%
- Frozen normalized universe: 2022-01-02 through 2024-12-31 inclusive
- Complete sessions: 1095
- B27FL 01:00 reproduction gate: PASS (162 causal leaves, 132 H2)
- Anchor remains frozen at 01:00 WIB; no clock re-selection
- No entry, TP, SL, PnL, fee, weekday filter, or holdout data used

## 1. Frozen terminal path after causal leave

| Terminal | Count | Share of 162 leaves |
|---|---:|---:|
| H2_ARRIVAL | 132 | 81.5% |
| OPPOSITE_BREAK_BEFORE_H2 | 9 | 5.6% |
| AMBIGUOUS_H2_VS_OPPOSITE_BREAK | 0 | 0.0% |
| NO_H2_BY_END | 21 | 13.0% |

## 2. H2 arrival timing

- Immediate H2 on first post-leave candle: **30/162 (18.5%)** of all leaves
- H2 timing quartiles among 132 H2 arrivals: p25=10.0m, median=25.0m, p75=45.0m, p90=95.0m

| Timing bucket | Count | Share of H2 arrivals |
|---|---:|---:|
| 1_BAR_5M | 30 | 22.7% |
| 2_BARS_10M | 16 | 12.1% |
| 3_BARS_15M | 8 | 6.1% |
| 4_6_BARS_20_30M | 30 | 22.7% |
| 7_12_BARS_35_60M | 25 | 18.9% |
| 13PLUS_BARS_65M_PLUS | 23 | 17.4% |

## 3. Pre-H2 pullback depth (terminal H2 candle excluded)

| Measure | p25 | Median | p75 | p90 |
|---|---:|---:|---:|---:|
| Low depth / R | 0.100 | 0.255 | 0.391 | 0.663 |
| Close depth / R | 0.048 | 0.187 | 0.336 | 0.619 |

## 4. Frozen completed-close pullback grid

- Nested threshold consistency P50 ⊆ P35 ⊆ P20 ⊆ P10: **PASS**
- Threshold must occur on a completed non-terminal candle; the terminal candle itself cannot create the prior pullback.

| Threshold | Reached before terminal | Share leaves | H2 | Opp | Amb | No H2 | H2 recovery | Median threshold→H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P10 (0.10R) | 111 | 68.5% | 82 | 9 | 0 | 20 | 73.9% | 30.0m |
| P20 (0.20R) | 93 | 57.4% | 64 | 9 | 0 | 20 | 68.8% | 35.0m |
| P35 (0.35R) | 57 | 35.2% | 31 | 9 | 0 | 17 | 54.4% | 55.0m |
| P50 (0.50R) | 42 | 25.9% | 20 | 9 | 0 | 13 | 47.6% | 57.5m |

## 5. First post-leave completed close segmentation

| First close depth | N | Share leaves | H2 | H2 outcome | Opp | Amb | No H2 | First bar itself H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LE_0.10R | 53 | 32.7% | 51 | 96.2% | 1 | 0 | 1 | 28 |
| GT_0.10_TO_0.20R | 55 | 34.0% | 44 | 80.0% | 2 | 0 | 9 | 1 |
| GT_0.20_TO_0.35R | 33 | 20.4% | 22 | 66.7% | 2 | 0 | 9 | 1 |
| GT_0.35_TO_0.50R | 14 | 8.6% | 11 | 78.6% | 3 | 0 | 0 | 0 |
| GT_0.50R | 6 | 3.7% | 4 | 66.7% | 1 | 0 | 1 | 0 |
| MISSING_FIRST_POST_LEAVE_BAR | 1 | 0.6% | 0 | 0.0% | 0 | 0 | 1 | 0 |

## Interpretation boundary

B27FM maps the causal structural path after the 01:00 WIB leave. Any high H2 recovery percentage is a structural outcome rate, not a trading win rate. The pullback grid is descriptive discovery only and no threshold is selected as an entry in this milestone.

**Status: B27FM_BNB_HOUR01_POST_LEAVE_SEQUENCE_COMPLETE**

STOP: any actual entry hypothesis, stop/target, or economic test requires a new preregistered milestone.
