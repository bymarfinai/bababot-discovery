# BTC Friday C5 — 15m Candle + Derivatives-State Result

Friday dates **139**; aligned rows **13253**; metrics rows **280054**
Integrity violations **0**; eligible discovery 80% leaves **0**

## CONT discovery leaves

| Leaf | Pred | N | Wins | WR | Rule |
|---:|---:|---:|---:|---:|---|
| 2 | 0 | 5842 | 1406 | 24.07% | `range_open <= 0.0059455675 AND top_vs_global <= 0.58402112` |
| 3 | 0 | 2016 | 276 | 13.69% | `range_open <= 0.0059455675 AND top_vs_global > 0.58402112` |
| 5 | 0 | 1269 | 518 | 40.82% | `range_open > 0.0059455675 AND top_vs_global <= 0.69571707` |
| 6 | 0 | 96 | 17 | 17.71% | `range_open > 0.0059455675 AND top_vs_global > 0.69571707` |

## REV discovery leaves

| Leaf | Pred | N | Wins | WR | Rule |
|---:|---:|---:|---:|---:|---|
| 2 | 0 | 5282 | 1202 | 22.76% | `range_open <= 0.004473092 AND top_vs_global <= 0.64138645` |
| 3 | 0 | 1497 | 191 | 12.76% | `range_open <= 0.004473092 AND top_vs_global > 0.64138645` |
| 5 | 0 | 2258 | 762 | 33.75% | `range_open > 0.004473092 AND top_vs_global <= 0.72769466` |
| 6 | 0 | 186 | 29 | 15.59% | `range_open > 0.004473092 AND top_vs_global > 0.72769466` |

## Verdict

**REJECT_C5_DERIVATIVES_IDENTIFIER**

No positive discovery derivatives leaf achieved N>=80 and WR>=80%.

All metrics are latest strictly-before-entry observations. No post-result derivatives/tree rescue.
