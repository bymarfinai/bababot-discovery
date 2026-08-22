# BTC 4H Regime + 15m EMA 1:1 B25A — Result

5m source rows: **698,112**; coverage: **100.0000%**

Frozen setup: 4H B21 bull regime already ON -> 15m EMA20/50 bullish cross -> first later green 15m candle while regime remains ON -> entry next 15m open -> TP +1% / SL -1%.

5m bars are used only to determine which fixed 1% barrier is touched first. If both barriers occur inside one 5m bar, the trade is counted conservatively as SL.

Illustration: $10 margin x 50x = $500 notional. Gross TP/SL = +/-$5. Illustrative round-trip fee = $0.40.

| Partition | Entered | Resolved | W | L | WR | Gross PF | Gross expectancy | Net expectancy/trade | Total net | Median hold min | Same-5m ambiguous | Partition gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| external | 210 | 210 | 109 | 101 | 51.90% | 1.08 | 0.04% | $-0.21 | $-44.00 | 142.5 | 0.00% | FAIL |
| development | 239 | 239 | 118 | 121 | 49.37% | 0.98 | -0.01% | $-0.46 | $-110.60 | 225.0 | 0.00% | FAIL |
| reference_validation | 111 | 111 | 57 | 54 | 51.35% | 1.06 | 0.03% | $-0.26 | $-29.40 | 375.0 | 0.00% | FAIL |
| august | 2 | 2 | 0 | 2 | 0.00% | 0.00 | -1.00% | $-5.40 | $-10.80 | 1040.0 | 0.00% | FAIL |

## Frozen overall gate

- B25A_REPEATABLE_1TO1_EDGE: **FAIL**

The overall gate requires external, development, and reference_validation each to have >=50 resolved trades, WR >=55%, and positive fee-sensitive expectancy.

Research only; live BBC unchanged.
