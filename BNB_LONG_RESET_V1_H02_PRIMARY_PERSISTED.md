# BNB LONG Reset V1 — H02 Primary Character PERSISTED / FROZEN

## Verdict

**PRIMARY_PASS**

Habitat: **02:00–03:00 WIB only**  
Selected primary character: **`rv_ratio_60_240__HIGH`**  
Feature: `rv_ratio_60_240`  
State: `HIGH`  
Development: **2022-01-01 through 2024-12-31 WIB**  
OOS: **SEALED — not downloaded / not evaluated**  
Search status: **STOP NEW-HOUR SCANNING**. H03 and later hours are blocked unless this promoted H02 character fails the preregistered downstream validation path.

The character means short-window realized volatility (60m) is in the **HIGH causal percentile state relative to 240m realized volatility**, using only information available before each anchor.

## Development sample and raw structural economics

Reference economics only: **$10 margin × 50x = $500 notional per signal**. Dollar figures below are raw structural-return equivalents, **not executable/net trading PnL**. TP/SL, fees, slippage, overlap, liquidation mechanics, and final execution are not applied yet.

| Metric | H02 selected primary |
|---|---:|
| Development events in H02 | 4,384 |
| Selected signals | **1,448** |
| Approx selected signals/week | **9.25** |
| Consensus WR | **57.32%** |
| Consensus mean return/signal | **0.0691%** |
| Consensus median return/signal | **0.0661%** |
| PF | **1.291** |
| Raw $/signal @ $500 notional | **+$0.35** |
| Raw cumulative equivalent | **+$499.93** |
| Gross positive equivalent | +$2,216.34 |
| Gross negative equivalent | -$1,716.41 |
| Avg winning signal | **+$2.67** |
| Avg losing signal | **-$2.78** |
| Raw max DD equivalent | **-$144.25** |
| Max loss streak | **12** |
| Supportive horizons | **2/3** |
| Supportive quarter-hour anchors | **4/4** |
| Years supportive | **3/3** |
| Years with WR >55% | **2/3** |
| Pooled gate | **PASS** |
| Horizon gate | **PASS** |
| Era gate | **PASS** |
| Anchor gate | **PASS** |
| Final Development gate | **PASS** |

## Cross-year robustness

| Year | N | WR | Mean return | Raw $/signal | Raw total | PF | Raw max DD | Max LS | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2022 | 454 | 58.59% | 0.0705% | +$0.35 | +$160.13 | 1.241 | -$144.25 | 12 | PASS |
| 2023 | 494 | 58.50% | 0.0680% | +$0.34 | +$167.95 | 1.381 | -$109.04 | 12 | PASS |
| 2024 | 500 | 55.00% | 0.0687% | +$0.34 | +$171.86 | 1.281 | -$87.84 | 10 | PASS |

2024 WR is exactly **55.00%**. It therefore does not count toward the separate `WR >55%` count, but it does pass the frozen per-year support gate (WR >=52%, positive mean, PF >=1.05, N >=40). All three years are supportive and 2/3 years are above 55% WR.

## Diagnostic horizons

| Horizon | N | WR | Mean return | Raw $/signal | Raw total | PF | Raw max DD | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 60m | 1,448 | 54.63% | 0.0109% | +$0.05 | +$79.07 | 1.051 | -$132.78 | FAIL |
| 120m | 1,448 | 55.25% | 0.0562% | +$0.28 | +$406.87 | 1.216 | -$195.21 | PASS |
| 240m | 1,448 | 59.60% | 0.1400% | +$0.70 | +$1,013.85 | 1.414 | -$188.12 | PASS |

60m is positive but fails the frozen horizon-support PF threshold (PF **1.051 < 1.10**). 120m and 240m pass, so the preregistered requirement of at least 2/3 supportive horizons is satisfied. This does **not** select 240m as the final holding period; hold/TP/SL belongs to later trade construction.

## Quarter-hour anchor robustness

| Entry WIB | N | WR | Mean return | Raw $/signal | Raw total | PF | Raw max DD | Max LS | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 02:00 | 363 | 54.82% | 0.0409% | +$0.20 | +$74.31 | 1.161 | -$58.90 | 11 | PASS |
| 02:15 | 361 | 55.40% | 0.0583% | +$0.29 | +$105.18 | 1.239 | -$46.66 | 7 | PASS |
| 02:30 | 365 | 59.73% | 0.0753% | +$0.38 | +$137.34 | 1.329 | -$45.03 | 5 | PASS |
| 02:45 | 359 | 59.33% | 0.1020% | +$0.51 | +$183.10 | 1.460 | -$38.61 | 4 | PASS |

All four anchors pass. The edge is not dependent on a single quarter-hour, although 02:30 and 02:45 are stronger than 02:00/02:15.

## Why H02 is promoted

- H00 had attractive pooled candidates but failed cross-era robustness, especially 2022.
- H01 had a positive `drive_240m__LOW` tendency but missed frozen pooled/era economics gates.
- H02 `rv_ratio_60_240__HIGH` passes **pooled + horizon + era + anchor** gates without rescue filters or threshold changes.

## Locked next state

1. `rv_ratio_60_240__HIGH` is frozen as the H02 primary character.
2. **Do not scan H03 or later hours.**
3. Next stage is secondary-confirmation / structural stress testing on this same H02 primary only.
4. Secondary confirmation may reduce noise but cannot replace or rescue the primary character.
5. OOS 2025-01-01 through 2026-07-30 remains sealed.
6. Only after structural promotion and OOS PASS: trade construction, hold/TP/SL, fees/slippage, overlap, leverage/execution, and READY-TO-TRADE validation.

Research/shadow only.
