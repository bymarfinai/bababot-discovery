# BTC Potential B Mirror — LOD Breakdown / Seller Trap BUY Result

**80% candidate gate: REJECT**

Frozen rule: weekdays; pre-07:00 UTC LOD; first two consecutive 5m closes below LOD during 07:00-08:30 UTC; BUY next causal 15m open; aggressive seller iff taker-buy share <50%.

## Historical 2023-12-02 to 2026-07-30

| Cohort | N | Wins | WR | Avg BUY ret | Median MFE | Median MAE |
|---|---:|---:|---:|---:|---:|---:|
| Base | 87 | 49 | 56.32% | 0.03% | 0.26% | 0.27% |
| Aggressive seller | 62 | 36 | 58.06% | 0.06% | 0.27% | 0.25% |

### Aggressive-seller chronology

| Split | N | Wins | WR |
|---|---:|---:|---:|
| Discovery first70% | 43 | 26 | 60.47% |
| Validation last30% | 19 | 10 | 52.63% |

| Block | N | Wins | WR |
|---|---:|---:|---:|
| B1 | 16 | 10 | 62.50% |
| B2 | 16 | 7 | 43.75% |
| B3 | 15 | 11 | 73.33% |
| B4 | 15 | 8 | 53.33% |

## Historical >1% diagnostic — aggressive seller

N **62**, wins **17**, WR **27.42%**, TP **17**, SL **45**, TIME **0**, PnL **$-186.50**.

## August 2026 true-OOS

| Cohort | N | Wins | 60m WR | Avg BUY ret |
|---|---:|---:|---:|---:|
| Base | 2 | 0 | 0.00% | -0.28% |
| Aggressive seller | 2 | 0 | 0.00% | -0.28% |

August aggressive >1% diagnostic: N **2**, wins **0**, WR **0.00%**, TP **0**, SL **2**, TIME **0**, PnL **$-11.50**.

## August event ledger

| UTC date | Entry WIB | LOD | Taker buy | Seller aggressive | 60m | BUY ret | 1%/6h | MFE6h |
|---|---|---:|---:|---|---|---:|---|---:|
| 2026-08-03 | 2026-08-03 14:30 | 62576.20 | 38.9% | YES | LOSS | -0.490% | SL_1PCT | 0.584% |
| 2026-08-14 | 2026-08-14 15:15 | 62900.20 | 45.3% | YES | LOSS | -0.067% | SL_1PCT | 0.141% |

No clock/window/flow/TP-SL parameter was selected from the result. Live BBC untouched.
