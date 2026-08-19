# BTC Friday All-Hour Candle C0 — Result

Friday dates: **142**; signal candles: **3407**
Discovery/validation Friday dates: **99 / 43**

## CONT tree discovery leaves

| Leaf | Pred | N | Wins | WR | Rule |
|---:|---:|---:|---:|---:|---|
| 2 | 0 | 752 | 260 | 34.57% | `close_pos <= 0.36064751 AND range_open <= 0.014041745` |
| 3 | 1 | 100 | 55 | 55.00% | `close_pos <= 0.36064751 AND range_open > 0.014041745` |
| 5 | 0 | 1407 | 633 | 44.99% | `close_pos > 0.36064751 AND body_ratio <= 0.80671072` |
| 6 | 1 | 117 | 70 | 59.83% | `close_pos > 0.36064751 AND body_ratio > 0.80671072` |

## REV tree discovery leaves

| Leaf | Pred | N | Wins | WR | Rule |
|---:|---:|---:|---:|---:|---|
| 2 | 0 | 102 | 39 | 38.24% | `close_pos <= 0.36064751 AND signal_ret <= -0.0088109463` |
| 3 | 1 | 750 | 409 | 54.53% | `close_pos <= 0.36064751 AND signal_ret > -0.0088109463` |
| 5 | 1 | 108 | 60 | 55.56% | `close_pos > 0.36064751 AND body_ratio <= 0.066112891` |
| 6 | 0 | 1416 | 578 | 40.82% | `close_pos > 0.36064751 AND body_ratio > 0.066112891` |

## Verdict

**REJECT_C0_80_CANDLE_IDENTIFIER**

No continuation/reversal discovery leaf met N>=100 and WR>=80%.

Observed historical WR is not a guaranteed future probability.
