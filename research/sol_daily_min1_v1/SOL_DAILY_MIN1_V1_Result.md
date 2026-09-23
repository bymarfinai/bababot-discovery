# SOL Daily-Min1 V1 — Extreme Reversion / Range Edge

**Status: HIGH_FREQUENCY_HISTORICAL_EDGE_FOUND__NEEDS_FRESH_FORWARD_CONFIRMATION**

## Goal
Find a SOL strategy that averages **at least 1 executed trade per day** while keeping positive historical expectancy across 2023-24, 2025, and 2026.

## Data
- SOLUSDT USD-M futures
- 1H candles
- 2023-01-01 through 2026-09-23
- 32,680 continuous 1H bars
- one position at a time

## Entry construction
1. Use the last **5 completed 1H candles**.
2. Compute average high-to-high and low-to-low ratios.
3. Predict next-hour high and low:
   - predicted_low = current_low * mean(low_t / low_{t-1})
   - predicted_high = current_high * mean(high_t / high_{t-1})
4. Place extreme limit zones:
   - LONG entry = predicted_low * 0.99
   - SHORT entry = predicted_high * 1.01
5. The next 1H candle is the fill candle.
6. If both LONG and SHORT levels are touched in the same fill candle, skip because intrabar order is unknown.

## Character filters
Only allow a candidate when:
- **72H range location <= 80%**
  - loc72 = (close - low72) / (high72 - low72)
  - avoids entering from the absolute top edge of the recent 72H structure.
- **signal candle directional body <= 15% of candle range**
  - body = (close-open)/(high-low)
  - rejects strongly impulsive bullish candles; allows small-body / neutral / bearish structure before extreme reversion entry.

## Exit
- TP = **+2.0%**
- SL = **-1.0%**
- reward:risk = **2:1**
- TP/SL monitoring begins from the 1H candle **after the fill candle**
- max holding horizon = **36h**
- if TP and SL are both inside one later 1H candle, count conservatively as LOSS.

## Results

### Development 2023-2024
- 1,144 trades
- 453 wins
- 689 losses (includes conservative ambiguous-loss treatment)
- 2 no-hit
- decided WR = **39.67%**
- gross expectancy = **+0.1897R/trade**
- trade frequency = **1.57/day**

### Reference 2025
- 500 trades
- 196 wins
- 304 losses
- decided WR = **39.20%**
- gross expectancy = **+0.1760R/trade**
- trade frequency = **1.37/day**

### 2026 through Sep 23
- 269 trades
- 105 wins
- 159 losses
- 5 no-hit
- decided WR = **39.77%**
- gross expectancy = **+0.1896R/trade**
- trade frequency = **1.015/day**

## Why low WR can still be strong
At 2:1 reward:risk the breakeven WR before costs is 33.33%.
Historical WR remains ~39-40% across all periods, producing ~+0.18R gross expectancy per trade.

## Robustness
Sensitivity scan varied:
- predictor window: 3, 5, 7, 10
- entry buffer: 0.75%, 1.0%, 1.25%
- loc72 cap: 80%, 82.5%, 85%
- body cap: 10%, 15%, 20%, 25%

**45 parameter combinations** remained:
- positive in 2023-24,
- positive in 2025,
- positive in 2026,
- and >=1 trade/day in every period.

Best plateau centered around:
- predictor window = 5
- buffer = 1%
- loc72 <= 80-82.5%
- body <= 15-20%

Representative nearby variants:
- loc72<=82.5%, body<=15%: +0.1786R / +0.1650R / +0.1942R, 1.64 / 1.41 / 1.05 trades/day
- loc72<=80%, body<=20%: +0.1840R / +0.1628R / +0.1808R, 1.62 / 1.41 / 1.02 trades/day

## High-WR alternative
Using TP=1%, SL=1% with high-frequency filters gives roughly:
- 2023-24: ~52-53% WR
- 2025: ~52%
- 2026: ~52-55% WR
- >1 trade/day

But gross expectancy is only ~+0.04R to +0.06R/trade and is much more vulnerable to fees/slippage. It is therefore not the preferred economic candidate.

## Interpretation
This is a different character from CCI.

CCI = rare continuation from compression.

Daily-Min1 V1 = **extreme-price entry / mean-reversion geometry**:
- use recent high/low drift to estimate next-hour extremes,
- wait for a 1% excursion beyond the predicted extreme,
- avoid a market already pinned at the upper edge of the 72H range,
- avoid chasing a strongly impulsive signal candle,
- enter from the extreme with asymmetric 2R payoff.

## Validation discipline
2026 was inspected during discovery, so it is not a pristine untouched holdout.
The strategy is a strong historical candidate, not a guaranteed live edge.
Next required step is frozen forward validation and 15m/1m intrabar execution verification, plus explicit fee/slippage accounting.
