# BTC Friday Pre-entry Fingerprint P2 — Shallow Tree Result

Discovery leaves: **4**

## Discovery leaves

| Leaf | Pred | N | Wins | WR | Rule |
|---:|---:|---:|---:|---:|---|
| 2 | 1 | 22 | 21 | 95.45% | `h1_close_pos <= 0.2455323 AND f5_upper_share_delta_prev3median <= 0.19466273` |
| 3 | 1 | 13 | 7 | 53.85% | `h1_close_pos <= 0.2455323 AND f5_upper_share_delta_prev3median > 0.19466273` |
| 5 | 0 | 14 | 1 | 7.14% | `h1_close_pos > 0.2455323 AND h1_upper <= 0.12025961` |
| 6 | 0 | 33 | 16 | 48.48% | `h1_close_pos > 0.2455323 AND h1_upper > 0.12025961` |

## Selected human-readable fingerprint

`h1_close_pos <= 0.2455323 AND f5_upper_share_delta_prev3median <= 0.19466273`

| Cohort | N | Wins | WR | PnL | Exp | PF |
|---|---:|---:|---:|---:|---:|---:|
| Discovery | 22 | 21 | 95.45% | $104.392 | $4.745 | 25.563 |
| Validation | 15 | 8 | 53.33% | $2.338 | $0.156 | 1.090 |
| Full | 37 | 29 | 78.38% | $106.730 | $2.885 | 4.542 |

### Chronological blocks

| Block | N | Wins | WR | PnL | PF |
|---|---:|---:|---:|---:|---:|
| B1 | 10 | 9 | 90.00% | $35.591 | 9.374 |
| B2 | 10 | 10 | 100.00% | $64.277 | 999.000 |
| B3 | 9 | 5 | 55.56% | $-3.029 | 0.769 |
| B4 | 8 | 5 | 62.50% | $9.891 | 1.776 |

## Verdict

**REJECT_P2_80_CANDLE_IDENTIFIER**

Observed historical WR is not a guaranteed future win probability.
