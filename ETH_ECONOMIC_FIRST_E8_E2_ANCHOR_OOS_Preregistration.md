# ETH Economic-First E8 — Raw E2 Anchor OOS Audit Preregistration

**PREREGISTERED before result-bearing execution.**

## Purpose
E7 proved that the high-WR TP ridge found on Development does not replicate economically. Before any further signal or management optimization, E8 tests one upstream question only:

> Does the original raw E2 anchor itself have positive economic sign outside Development?

This is a one-coordinate audit. There is no candidate search, ranking, threshold rescue, or second-best substitution.

## Frozen coordinate
- ETHUSDT Binance Futures raw 5m
- weekdays only
- entry clock: **17:00 UTC (00:00 WIB)**
- pre-entry lookback: **360m**
- response: **MOMENTUM** (LONG after positive drive, SHORT after negative drive)
- entry: exact 17:00 5m open
- exit: exact open **720m** later
- no strength filter
- no TP / no SL
- $500 fixed notional
- $0.75 round-trip fee
- no compounding
- no H/L/reference range/breakout/retest/EMA/Fibonacci

## Partitions
- External: 2020-01-01 to 2022-01-01 UTC
- Development: 2022-01-01 to 2025-01-01 UTC
- Reference Validation: 2025-01-01 to 2026-07-30 UTC

## Development reproduction check
The same E2 implementation must reproduce the previously published Development anchor approximately:
- N **781**
- WR **47.63%**
- net **+$481.58**
- expectancy **+$0.62/trade**
- PF **1.155**
- max DD **$315.01**

If reproduction materially fails, the run is invalid.

## OOS economic-sign rule
For each OOS partition independently require:
- >=300 trades
- net PnL >0
- expectancy >0
- PF >1.00

WR, DD, and streaks are reported but do not determine this narrow upstream audit. The goal is only to establish whether the raw anchor has positive economic sign before management.

## Decision
- both OOS partitions pass -> `ETH_ECONOMIC_FIRST_E8_RAW_ANCHOR_SIGN_REPLICATED`
- either OOS partition fails -> `ETH_ECONOMIC_FIRST_E8_RAW_ANCHOR_NOT_REPLICATED`
- reproduction failure -> invalid run

If the raw anchor does not replicate, close the 17:00/LB360 raw-anchor lineage; do not rescue it with another TP/hold using already-opened OOS data. If it does replicate, future work may study a management rule using Development only.

Research/shadow only. No live promotion or profit guarantee.
