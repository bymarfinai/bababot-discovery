# B27E — BTC 4H Same-Side Swing Touches Before Breakout

Source coverage: **100.0000%**. 4H causal swing breakout -> next 4H open -> breakout-candle opposite extreme SL -> 2R TP.

Touch = distinct rejection visit to the SAME swing boundary before the final close-through breakout. Consecutive touching candles count as one visit. New same-side swing level resets that side count.

| Partition | Prior touches | Resolved | LONG N | SHORT N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop | Median hold min |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | ALL | 229 | 139 | 91 | 77 | 152 | 33.62% | 0.94 | $-0.60 | $-137.24 | 2.36% | 925.0 |
| external | 0 | 172 | 107 | 66 | 56 | 116 | 32.56% | 0.90 | $-1.11 | $-190.22 | 2.45% | 987.5 |
| external | 1 | 57 | 32 | 25 | 21 | 36 | 36.84% | 1.13 | $0.93 | $52.97 | 1.98% | 740.0 |
| external | 2 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| external | 3 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| external | 4+ | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| development | ALL | 358 | 186 | 173 | 126 | 232 | 35.20% | 1.00 | $0.02 | $6.30 | 1.68% | 922.5 |
| development | 0 | 253 | 128 | 126 | 89 | 164 | 35.18% | 0.99 | $-0.04 | $-10.36 | 1.76% | 985.0 |
| development | 1 | 105 | 58 | 47 | 37 | 68 | 35.24% | 1.03 | $0.16 | $16.66 | 1.50% | 795.0 |
| development | 2 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| development | 3 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| development | 4+ | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| reference_validation | ALL | 244 | 136 | 109 | 76 | 168 | 31.15% | 0.83 | $-0.92 | $-224.58 | 1.31% | 857.5 |
| reference_validation | 0 | 172 | 104 | 69 | 50 | 122 | 29.07% | 0.72 | $-1.68 | $-289.76 | 1.36% | 1087.5 |
| reference_validation | 1 | 72 | 32 | 40 | 26 | 46 | 36.11% | 1.20 | $0.91 | $65.18 | 1.00% | 507.5 |
| reference_validation | 2 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| reference_validation | 3 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| reference_validation | 4+ | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| august | ALL | 7 | 5 | 3 | 1 | 6 | 14.29% | 0.42 | $-2.48 | $-17.36 | 1.12% | 1020.0 |
| august | 0 | 5 | 3 | 3 | 1 | 4 | 20.00% | 0.53 | $-2.28 | $-11.41 | 1.17% | 1385.0 |
| august | 1 | 2 | 2 | 0 | 0 | 2 | 0.00% | 0.00 | $-2.97 | $-5.95 | 0.51% | 562.5 |
| august | 2 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| august | 3 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| august | 4+ | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |

## Pre-registered repeatability verdict by prior-touch bucket

- 0 prior touches: **FAIL / INSUFFICIENT**
- 1 prior touches: **FAIL / INSUFFICIENT**
- 2 prior touches: **FAIL / INSUFFICIENT**
- 3 prior touches: **FAIL / INSUFFICIENT**
- 4+ prior touches: **FAIL / INSUFFICIENT**

A bucket requires >=30 resolved trades AND positive net expectancy AND net PF >=1.20 in external, development, and reference_validation.

Research only; live BBC unchanged.
