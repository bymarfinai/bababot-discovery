# BNB B29 A4 — Selective Character Evidence Result

**Status: BNB_B29_A4_SELECTIVE_EVIDENCE_REJECT**

A4 applies an outcome-blind sparse evidence gate to the frozen A3 regime-aware character memory. No entry, TP, SL, leverage, fees, PnL or live orders are tested.

## Frozen identity

- A1 fingerprint hash: `2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6`
- Frozen A1 hash match: **PASS**
- Raw 5m coverage: 100.000000%
- Post-cutoff data touched: **NO**
- A3 parent queries: 10,185
- A4 EVIDENCE_READY queries: 130
- Pooled selected coverage: 1.28%

## Walk-forward folds

| Fold | Parent N | Ready N | Coverage | Mean directional hit | Median rho | Similarity | Structure | Path | Median regime N | Median abs pred |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 2,189 | 10 | 0.46% | 36.00% | -0.1636 | 35.50% | 64.84% | 68.75% | 10,846 | 0.13% |
| 2023 | 2,190 | 15 | 0.68% | 52.00% | -0.1214 | 36.18% | 75.00% | 62.50% | 14,187 | 0.13% |
| 2024 | 2,195 | 30 | 1.37% | 51.33% | 0.1462 | 36.06% | 77.34% | 67.19% | 18,480 | 0.15% |
| 2025 | 2,190 | 41 | 1.87% | 49.76% | 0.0373 | 36.22% | 78.12% | 71.88% | 22,804 | 0.12% |
| 2026 | 1,421 | 34 | 2.39% | 45.29% | -0.1749 | 36.73% | 78.12% | 75.78% | 21,184 | 0.10% |

## Pooled fixed-horizon behaviour

| Horizon | N | Directional hit | Spearman rho |
|---:|---:|---:|---:|
| +15m | 130 | 45.38% | -0.0533 |
| +30m | 130 | 46.92% | -0.0127 |
| +60m | 130 | 54.62% | -0.0074 |
| +120m | 130 | 55.38% | 0.0283 |
| +360m | 130 | 38.46% | -0.2019 |

## Frozen gates

- Exact A1 / boundary / chronology / finite / clause integrity: **PASS**
- Each fold Ready N >=50: **FAIL**
- Each fold coverage 1%-35%: **FAIL**
- Pooled coverage <=25%: **PASS** (1.28%)
- Mean directional hit: **48.15%** (need >=52.50%)
- Pooled horizons >=52% hit: **2/5** (need >=4)
- Median pooled rho: **-0.0127** (need >=0.0400)
- Positive chronological folds: **2/5** (need >=4)
- No fold mean hit below 50%: **FAIL**
- 2025 mean hit: **49.76%** (need >=51.50%)
- 2026 mean hit: **45.29%** (need >=51.50%)
- Mean sign lift vs A3: **-2.46pp** (need >=+1.50pp)
- Median-rho lift vs A3: **-0.0325** (need >=+0.0150)
- Aggregate behavioural gate: **FAIL**

## Decision

**BNB_B29_A4_SELECTIVE_EVIDENCE_REJECT**

Frozen stop rule applies to this A4 identity. No live orders were placed.
