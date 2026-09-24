# SOL MTF 15M Character V1 — Result

Run: GitHub Actions 35941472400
Head: e8c9bb3e40ee642963dde801c6f0652f52a4fbd0
Status: NO_FULL_PASS__CHARACTER_FRONTIER_MAPPED

## Frozen target
TP +1.0%, WR >=70%, >=1 trade/day, positive after-cost expectancy in 2023-24 / 2025 / 2026, one position active.

## Coverage
- 5m data coverage: 99.76977%
- Complete 15m bars: 208,004
- Tested configurations: 1,728
- Full target passes: 0
- Positive-economics + >=1/day all-period configs: 0

## High-frequency frontier
SR_ANY, lookback 4x15m, close_loc >=0.55, depthATR >=0.00, context LOC80_4H_ABOVE, SL 1.50%:
- 2023-24: WR 59.9%, 1.52 trades/day, net expectancy -0.148%/trade
- 2025: WR 57.1%, 1.18 trades/day, net expectancy -0.219%/trade
- 2026: WR 57.1%, 1.07 trades/day, net expectancy -0.194%/trade
- worst-period WR 57.1%

Broader high-frequency SR_ANY / LOC80:
- 2023-24: WR 58.3%, 3.39/day, -0.185%/trade
- 2025: WR 57.3%, 3.33/day, -0.215%/trade
- 2026: WR 57.7%, 2.46/day, -0.178%/trade

## Highest robust-WR frontier
SR_DISP, lookback 24x15m, close_loc >=0.65, depthATR >=0.00, context LOC80_4H_ABOVE, SL 1.50%:
- 2023-24: WR 59.7%, 0.24/day, -0.145%/trade
- 2025: WR 57.4%, 0.15/day, -0.201%/trade
- 2026: WR 61.0%, 0.25/day, -0.119%/trade
- worst-period WR 57.4%

## Verdict
Simple 15m sweep/reclaim, bullish-body, displacement, and follow-through triggers conditioned only by completed 1H 72h-range location and completed 4H EMA20 context do not bridge the frequency-vs-WR gap.

The next discovery step should not tune these thresholds. Decompose the high-frequency candidate's wins/losses using richer pre-entry 15m path features and identify causal separators before testing a new frozen detector.
