# BTC Strong Trend Transition Atlas B23B — Preregistration

## Purpose
Forensically map the candle-by-candle lifecycle of every previously frozen STRONG uptrend episode from B23A without selecting a trading entry or optimizing a TP/SL.

## Data and partitions
Reuse the same BTCUSDT 5m source, causal resampling, EMA20/EMA50 calculations, partitions, and STRONG definition as B23A.

## Frozen states
Each completed candle after a STRONG onset is classified causally, in this precedence order:

1. REVERSAL
   - close < EMA50, OR
   - EMA20 < EMA50, OR
   - close < EMA20 AND EMA20 < EMA20[1] AND spread < spread[1].
2. STRONG
   - EMA20 > EMA50,
   - EMA20 > EMA20[3],
   - EMA50 > EMA50[3],
   - spread > spread[3],
   - close > EMA20.
3. HEALTHY
   - EMA20 > EMA50,
   - close >= EMA20,
   - EMA20 >= EMA20[1],
   - not STRONG and not REVERSAL.
4. WEAKENING
   - EMA20 > EMA50,
   - close >= EMA50,
   - not STRONG, not HEALTHY, and not REVERSAL.

An episode begins at the first STRONG candle after the previous episode ended and ends at the first REVERSAL candle.

## Outputs
For every timeframe 5m, 15m, 1h, 4h and chronological partition:
- episode count;
- dominant compressed state path after STRONG onset;
- probability that REVERSAL is preceded by at least one HEALTHY or WEAKENING candle;
- probability of a direct STRONG -> REVERSAL transition;
- median bars from first non-STRONG candle to REVERSAL;
- median bars spent in STRONG, HEALTHY, and WEAKENING before REVERSAL;
- distribution of the final pre-reversal state;
- median return captured if exit occurred at the next open after first WEAKENING versus next open after REVERSAL, reported for diagnosis only.

## Interpretation rules
This experiment is an episode atlas, not a strategy promotion test. No state thresholds may be changed after results. No live BBC code is touched.