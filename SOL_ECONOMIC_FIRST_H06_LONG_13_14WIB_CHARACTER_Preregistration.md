# SOL Economic-First H06 — One-Hour LONG Character Discovery

## Scientific question

Within **06:00–07:00 UTC / 13:00–14:00 WIB** only, what causal pre-entry character produces robust high-WR positive SOL LONG economics?

H06 is independent of H00–H05. It inherits no earlier winner or clue, legacy SOL parent, Fibonacci coordinate, visit-order structure, target, stop, or recovery rule.

## Frozen scope

- SOLUSDT Binance Futures raw 5m; weekdays; LONG only.
- Anchors: **06:00, 06:15, 06:30, 06:45 UTC** = 13:00, 13:15, 13:30, 13:45 WIB.
- Exact 5m-open entry; exact 5m-open fixed-time exit.
- Fixed notional $500; round-trip fee $0.75.
- No TP, SL, Fibonacci, reference range, visit, breakout, retest, or EMA.
- Development 2022–2024 only. External and Reference Validation remain closed.

## Candidate universe

- Lookbacks: **15, 30, 60, 120, 240, 360 minutes**.
- Holds: **60, 120, 240, 360, 720, 960 minutes**.
- Exactly **90 frozen causal character rules** covering direction, causal drive-strength quintiles, LOW/MID/HIGH efficiency/volatility/range/terminal-location states, frozen two-state interactions, and direction-state interactions.
- Total candidates: **90 x 6 x 6 = 3,240**.

Each state uses only up to the previous 60 same-anchor/same-lookback observations, requires 40 historical observations, and excludes the current observation from its percentile.

## Frozen gates

An anchor is evaluable at N >= 40 and supportive at WR >= 52%, positive net and expectancy, PF >= 1.05, DD <= $125, and loss streak <= 10. Candidate anchor gate: at least 3/4 evaluable and 3/4 supportive.

Pooled gate: N >= 160, WR >= 55%, positive net, expectancy >= +$0.50, PF >= 1.20, DD <= $125, and loss streak <= 8.

For every Development year: N >= 40, WR >= 52%, positive net/expectancy, and PF >= 1.05; at least two years require WR >= 55%.

## Frozen ranking and decision

Rank full passers by minimum yearly expectancy, supportive anchors, pooled expectancy, WR, PF, lower DD, lower loss streak, shorter hold, shorter lookback, then lexical rule. Select exactly the top passer as `SOL_ECONOMIC_FIRST_H06_LONG_CHARACTER_FOUND`; if none, mark `SOL_ECONOMIC_FIRST_H06_NO_LONG_CHARACTER`.

No relaxation, rounding rescue, OOS exposure, or inherited candidate privilege. The next hour must reopen all 3,240 candidates. Overlapping-hold economics are discovery diagnostics, not executable portfolio-return claims.

Research/shadow only.
