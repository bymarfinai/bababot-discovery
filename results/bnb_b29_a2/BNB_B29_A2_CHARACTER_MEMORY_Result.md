# BNB B29 A2 — Character Memory Result

**Status: BNB_B29_A2_CHARACTER_MEMORY_REJECT**

A2 evaluates walk-forward structural similarity and forward price behaviour only. It does not define or test entry, TP, SL, leverage, fees, PnL, or live execution.

## Frozen representation / data

- A1 fingerprint hash: `2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6`
- Frozen A1 hash match: **PASS**
- Raw 5m coverage: 100.000000%
- Post-2026-08-26 00:00:00+00:00 data touched: **NO**
- Evaluable sampled queries: 10,185

## Walk-forward folds

| Fold | Memory N | Query N | Evaluable | Median analog N | Similarity | Same structure | Same path | Median rho | Mean sign | Chronology |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2022 | 66,247 | 2,189 | 2,189 | 64 | 0.3552 | 59.38% | 65.62% | -0.0016 | 50.33% | PASS |
| 2023 | 101,283 | 2,190 | 2,190 | 64 | 0.3591 | 57.81% | 67.19% | -0.0093 | 49.56% | PASS |
| 2024 | 136,322 | 2,195 | 2,195 | 64 | 0.3689 | 64.06% | 70.31% | 0.0395 | 51.35% | PASS |
| 2025 | 171,453 | 2,190 | 2,190 | 64 | 0.3730 | 68.75% | 73.44% | 0.0352 | 52.02% | PASS |
| 2026 | 206,491 | 1,421 | 1,421 | 64 | 0.3790 | 67.19% | 73.44% | 0.0100 | 50.27% | PASS |

## Pooled fixed-horizon behaviour

| Horizon | N | Spearman rho | Sign agreement |
|---:|---:|---:|---:|
| +15m | 10,185 | 0.0209 | 50.70% |
| +30m | 10,185 | 0.0350 | 51.23% |
| +60m | 10,185 | 0.0200 | 50.55% |
| +120m | 10,185 | 0.0066 | 50.65% |
| +360m | 10,185 | 0.0073 | 50.56% |

## Frozen gates

- Coverage: **PASS**
- A1 hash guard: **PASS**
- Schema guard: **PASS**
- Frozen boundary: **PASS**
- Numeric finite: **PASS**
- Memory-size gate: **PASS**
- Query-count gate: **PASS**
- Analog-count gate: **PASS**
- Chronology / behaviour-known gate: **PASS**
- Structural coherence: **PASS** (median structure 64.06%, path 70.31%)
- Positive pooled horizons: **5/5** (need >=4)
- Median pooled rho: **0.0200** (need >=0.0300)
- Mean pooled sign agreement: **50.74%** (need >=50.50%)
- Positive chronological folds: **3/5** (need >=3)
- Aggregate character-memory gate: **FAIL**

## Decision

**BNB_B29_A2_CHARACTER_MEMORY_REJECT**

If PASS, freeze A2 as a reusable BNB character-memory layer before any entry/TP/SL work. If REJECT, do not tune this A2 identity against the same results.

No live orders were placed.
