# BNB R5 H00 — Micro RR 1:2 Character Discovery Preregistration

## Purpose
Identify whether BNBUSDT has a fast 00:00–01:00 WIB intraday character capable of very high TP-first hit rate with fixed RR 1:2 economics.

This is a separate research track from the frozen H22 R4d strategy.

## Frozen execution geometry
- Pair: BNBUSDT
- Habitat: 00:00–01:00 WIB only
- Anchors: 00:00, 00:15, 00:30, 00:45 WIB
- Directions: LONG and SHORT compete symmetrically
- Entry: anchor open, using only information available at that instant
- TP distance: +0.30% in trade direction
- SL distance: -0.15% in trade direction
- Nominal RR: 1 risk : 2 reward
- Maximum holding windows: 15, 30, 60, 90, 120 minutes
- If TP and SL are both inside the same 5m candle, score the event conservatively as SL-first
- If neither barrier is touched before max hold, exit at the open at max-hold timestamp
- Notional: $500/trade
- Base fee: $0.75/trade
- Slippage stress: 0, 2, 5, 10 bps per side
- Weekday-only signal universe is retained from the existing causal character engine for comparability

## Frozen character search space
- Lookbacks: 15, 30, 60, 120, 240, 360 minutes
- Existing causal 90-rule character grammar from E12/B28/R4b
- Directions: LONG, SHORT
- Max holds: 15, 30, 60, 90, 120 minutes
- Total cells: 6 × 90 × 2 × 5 = 5,400

No TP, SL, rule grammar, lookback, direction, anchor, or max-hold value may be added after results are observed.

## Data split
- Development/ranking: 2022–2024 only
- Historical holdout diagnostic: 2025 only
- 2026 remains closed

2025 is strategy-specific holdout for this R5 search, but is not claimed to be globally pristine because prior BNB studies have inspected 2025 outcomes.

## Development eligibility
A cell is eligible for ranking only if:
- pooled 2022–2024 N >= 150
- each year N >= 40
- pooled TP-first rate >= 70%
- minimum annual TP-first rate >= 65%
- net PnL > 0 in every development year at 0 bps
- pooled expectancy > 0
- pooled PF >= 1.20
- pooled max DD <= $160
- at least 3 of 4 anchors have N >= 25 and TP-first rate >= 65%

## High-WR target
A development cell is a formal high-WR target hit if, in addition to eligibility:
- pooled TP-first rate >= 80%
- minimum annual TP-first rate >= 75%
- pooled 2-bps/side expectancy > 0
- pooled 2-bps/side PF >= 1.15

## Frozen ranking
Rank eligible cells by:
1. formal high-WR target hit (True first)
2. higher minimum annual TP-first rate
3. higher pooled TP-first rate
4. higher trade count
5. higher pooled 2-bps expectancy
6. higher pooled 0-bps expectancy
7. higher pooled PF
8. lower max DD
9. shorter max hold
10. shorter lookback
11. deterministic rule/direction tie break

Only the #1 development-ranked cell is opened on 2025.

## 2025 diagnostic
Report N, TP-first rate, net win rate, Net, expectancy, PF, DD, loss streak and slippage stress.

A strong 2025 continuation is descriptive evidence, not permission to retune the frozen cell.

## Integrity
- No look-ahead.
- Same-bar TP/SL ambiguity is always resolved against the strategy.
- 2025 cannot alter selection.
- 2026 must remain unopened.
- If no >=80% development character exists, report the strongest eligible near-miss rather than relaxing gates.
- Research/shadow only; no guarantee of future profitability.
