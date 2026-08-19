# BTC Friday C4 — 15m Candle + Taker-Flow Result

Friday dates **141**; signal rows **13531**; eligible discovery 80% leaves **0**

## CONT discovery leaves

| Leaf | Pred | N | Wins | WR | Rule |
|---:|---:|---:|---:|---:|---|
| 2 | 0 | 3093 | 496 | 16.04% | `range_open <= 0.0050253326 AND range_open <= 0.0023152942` |
| 3 | 0 | 4286 | 1029 | 24.01% | `range_open <= 0.0050253326 AND range_open > 0.0023152942` |
| 5 | 0 | 1013 | 316 | 31.19% | `range_open > 0.0050253326 AND range_open <= 0.0068899249` |
| 6 | 0 | 1013 | 421 | 41.56% | `range_open > 0.0050253326 AND range_open > 0.0068899249` |

## REV discovery leaves

| Leaf | Pred | N | Wins | WR | Rule |
|---:|---:|---:|---:|---:|---|
| 2 | 0 | 2510 | 420 | 16.73% | `range_open <= 0.004473092 AND range_open <= 0.0020884473` |
| 3 | 0 | 4374 | 992 | 22.68% | `range_open <= 0.004473092 AND range_open > 0.0020884473` |
| 5 | 0 | 1868 | 551 | 29.50% | `range_open > 0.004473092 AND range_open <= 0.0081240186` |
| 6 | 0 | 653 | 262 | 40.12% | `range_open > 0.004473092 AND range_open > 0.0081240186` |

## Verdict

**REJECT_C4_TAKER_IDENTIFIER**

No positive discovery leaf achieved N>=100 and WR>=80%.

Observed historical WR is not a guaranteed future probability. No post-result tree/threshold rescue.
