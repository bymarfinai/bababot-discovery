# BNB B29-B2 — Frozen Character Entry Discovery Result

**Status: BNB_B29_B2_ENTRY_DISCOVERY_REJECT**

B2 tests only preregistered causal entry timing/mechanisms on the frozen B1J LONG character. No TP, SL, leverage, fees, PnL dollars or live orders are tested.

## Integrity

- Accepted A1 SHA256: `eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa`
- Exact immutable A1 identity: **PASS**
- Frozen B1J character event set: **PASS** (451 events)
- Era counts: {2022: 97, 2023: 82, 2024: 114, 2025: 93, 2026: 65}
- Gap-safe finite entry outcomes: **PASS**

## Development policy screen (2022-2024)

| Policy | N | Part. | Primary hit | Wilson | Worst era | 2022 | 2023 | 2024 | t+120 hit | Entry+60 hit | BH q | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| E0_EVENT_CLOSE | 293 | 100.00% | 61.09% | 55.40% | 58.54% | 60.82% | 58.54% | 63.16% | 58.02% | 61.09% | 0.000291258 | PASS |
| E15_HOLD | 268 | 91.47% | 63.06% | 57.13% | 61.80% | 61.80% | 64.10% | 63.37% | 54.48% | 58.96% | 0.000113081 | REJECT |
| E15_ANY | 293 | 100.00% | 61.77% | 56.09% | 60.82% | 60.82% | 63.41% | 61.40% | 55.63% | 58.36% | 0.000165436 | REJECT |
| E15_UP | 160 | 54.61% | 61.88% | 54.15% | 59.68% | 64.81% | 61.36% | 59.68% | 49.38% | 57.50% | 0.00276311 | REJECT |
| E15_UP_HOLD | 160 | 54.61% | 61.88% | 54.15% | 59.68% | 64.81% | 61.36% | 59.68% | 49.38% | 57.50% | 0.00276311 | REJECT |
| E15_PULLBACK_HOLD | 108 | 36.86% | 64.81% | 55.44% | 57.14% | 57.14% | 67.65% | 69.23% | 62.04% | 61.11% | 0.00276311 | REJECT |
| E15_PULLBACK | 133 | 45.39% | 61.65% | 53.17% | 55.81% | 55.81% | 65.79% | 63.46% | 63.16% | 59.40% | 0.00645035 | REJECT |
| E30_HOLD | 257 | 87.71% | 54.09% | 47.98% | 51.19% | 51.19% | 52.70% | 57.58% | 52.53% | 54.09% | 0.132568 | REJECT |
| E30_PULLBACK_RECOVER | 77 | 26.28% | 48.05% | 37.25% | 46.67% | 50.00% | 47.62% | 46.67% | 58.44% | 57.14% | 0.750672 | REJECT |
| E30_TWO_UP | 85 | 29.01% | 43.53% | 33.50% | 33.33% | 34.48% | 33.33% | 55.26% | 40.00% | 42.35% | 0.90362 | REJECT |

## Frozen shortlist

| Rank | Policy | N dev | Hit dev | Worst dev | Wilson |
|---:|---|---:|---:|---:|---:|
| 1 | E0_EVENT_CLOSE | 293 | 61.09% | 58.54% | 55.40% |

## Reference validation (2025-2026)

| Rank | Policy | 2025 N/hit | 2026 N/hit | Ref hit | Ref t+120 | Ref entry+60 | Pooled hit | Pooled Wilson | Gate |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | E0_EVENT_CLOSE | 93 / 55.91% | 65 / 58.46% | 56.96% | 58.23% | 56.96% | 59.65% | 55.05% | REJECT |

## Five-era primary-hit detail

| Rank | Policy | 2022 | 2023 | 2024 | 2025 | 2026 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | E0_EVENT_CLOSE | 60.82% | 58.54% | 63.16% | 55.91% | 58.46% |

## Decision

**BNB_B29_B2_ENTRY_DISCOVERY_REJECT**

No preregistered entry policy passed every development and reference gate. Do not proceed to TP/SL from B2-v1.

No live orders were placed.
