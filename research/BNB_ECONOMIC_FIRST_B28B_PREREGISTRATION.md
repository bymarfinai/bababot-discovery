# BNB Economic-First B28B — Preregistration

## Scope
- Pair: **BNBUSDT**
- Direction: **LONG only**
- Time habitat: **01:00–02:00 WIB only**
- Quarter-hour anchors: **01:00, 01:15, 01:30, 01:45 WIB** (18:00, 18:15, 18:30, 18:45 UTC)
- Development only; OOS/holdout remains closed.
- $500 notional per trade.
- No TP / no SL; causal fixed-horizon hold only.

## Frozen methodology
Use the exact same B28A economic-first engine without modification:
- neutral 90-rule causal character grammar,
- lookbacks 15 / 30 / 60 / 120 / 240 / 360 minutes,
- holds 60 / 120 / 240 / 360 / 720 / 960 minutes,
- 3,240 candidate identities,
- identical fee model,
- identical candidate ranking,
- identical anchor-stability gate,
- identical pooled economics/risk gate,
- identical 2022/2023/2024 all-era gate.

The **only changed variable is the one-hour habitat**.

## Information boundary
The B28A winner `EFF_LOW__RV_MID / LB30 / hold720m` is frozen but receives **no preference or bonus** in B28B. B27 H2/leave, P10 and structural coordinates remain excluded from selection/ranking. They may only be used later as post-selection explanatory diagnostics.

## Anti-overfit rules
- No SHORT search.
- No TP/SL tuning.
- No weekday filtering.
- No gate relaxation.
- No post-result clock rescue.
- No lookback/hold expansion.
- No OOS exposure.
- No substitution of a higher-WR row that fails the full gate.

## Decision
If one or more candidates pass the frozen full gate, select the top preregistered-ranked candidate and mark `BNB_ECONOMIC_FIRST_B28B_LONG_CHARACTER_FOUND`.

Otherwise mark `BNB_ECONOMIC_FIRST_B28B_NO_LONG_CHARACTER`, persist the strongest descriptive clues without promotion, and continue unchanged to **02:00–03:00 WIB**.

Research/shadow only. No live promotion or profit guarantee.