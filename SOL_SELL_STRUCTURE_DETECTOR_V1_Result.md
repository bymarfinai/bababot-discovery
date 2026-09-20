# SOL SELL Structure Detector V1 — Result

- 5m data coverage: **99.769767%**
- Development window: **2020-2024**; 2025+ remained CLOSED.
- Detector grammar: **buy-side liquidity sweep -> bearish displacement/BOS -> corrective return to bearish origin/break block -> rejection -> SHORT activation**.
- This run evaluates detector structure first; +60m short return is diagnostic only.

## Structural funnel

| Stage | Meaning | N | Conversion |
|---|---|---:|---:|
| A | Buy-side liquidity sweep/rejection | 948 | 100.00% |
| B | Bearish displacement + significant-low BOS + origin block | 157 | 16.56% |
| C | First corrective return into origin/break block | 136 | 86.62% |
| D | 5m rejection + SHORT activation | 92 | 67.65% |

Full-chain retention A -> D: **9.70%**

## Timing anatomy

- Median sweep -> BOS: **5.0 H1 bars**
- Median BOS -> first block return: **337.5 minutes**
- Median first return -> activation: **5.0 minutes**

## Fixed +60m SHORT diagnostic

| N | WR60 | Exp60 | PF | PnL | Max DD | Max LS | MFE | MAE | MFE/MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 92 | 43.48% | -0.3088% | 0.438 | USD -142.05 | USD 166.79 | 11 | 0.622% | 0.563% | 1.095 |

## Yearly diagnostic

| Year | N | WR60 | Exp60 | PF | PnL |
|---:|---:|---:|---:|---:|---:|
| 2020 | 7 | 42.86% | 0.1416% | 1.386 | USD 4.96 |
| 2021 | 20 | 55.00% | -0.5813% | 0.277 | USD -58.13 |
| 2022 | 26 | 42.31% | -0.3978% | 0.383 | USD -51.72 |
| 2023 | 18 | 22.22% | -0.4434% | 0.213 | USD -39.90 |
| 2024 | 21 | 52.38% | 0.0262% | 1.111 | USD 2.75 |

## Interpretation

Stage D is the exact full detector chain. The important result at this phase is whether the four structural blocks can be found causally and how much each stage narrows the universe.
Do not retune the frozen sweep, BOS, origin-zone, return, or rejection definitions on 2020-2024 after seeing this result. Any structural revision must be a new preregistered detector version.

OFFICIAL_STATUS=FULL_CHAIN_FOUND
FULL_MATCHES=92
2025_PLUS=CLOSED
