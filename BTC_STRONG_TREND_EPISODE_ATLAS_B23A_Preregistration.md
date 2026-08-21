# BTC Strong Trend Episode Atlas B23A — Preregistration

## Purpose
This is a forensic lifecycle study, not a strategy optimization. It tests the observation that once BTC enters a visually clean EMA20/EMA50 strong-uptrend state, the state normally persists for a meaningful interval before a true reversal rather than flipping immediately.

B22H is not reused as evidence for this question because its trade universe was restricted to `PULLBACK_RECLAIM` entries. B23A instead enumerates all strong-uptrend episodes.

## Data
- BTCUSDT futures 5m source used by B21/B22.
- Timeframes: 5m, 15m, 1h, 4h.
- Chronological partitions remain:
  - external: 2020-01-01 to 2022-01-01 UTC
  - development: 2022-01-01 to 2025-01-01 UTC
  - reference_validation: 2025-01-01 to 2026-07-30 UTC
  - August 2026: diagnostic only.

## Candle-causal indicators
EMA20 and EMA50 are computed from completed candles only.

### STRONG
At candle close:
- EMA20 > EMA50
- EMA20 > EMA20 three bars ago
- EMA50 > EMA50 three bars ago
- `(EMA20-EMA50)/close` > its value three bars ago
- close > EMA20

### REVERSAL
At candle close, first occurrence of any:
- close < EMA50; or
- EMA20 < EMA50; or
- close < EMA20 AND EMA20 < prior EMA20 AND EMA spread narrows vs prior candle.

### Intermediate states
For description only:
- HEALTHY: EMA20 > EMA50, EMA50 non-declining over three bars, close >= EMA50, not STRONG, not REVERSAL.
- WEAKENING: neither STRONG nor HEALTHY nor REVERSAL while an episode is active.

## Episode definition
An episode begins at the close of the first STRONG candle while no bull episode is active. It becomes tradable only from the next candle open, but B23A does not optimize or promote an entry.

Once active, an episode remains the same episode through STRONG, HEALTHY, and WEAKENING states. It ends only at the first REVERSAL candle. This means a healthy pullback or temporary loss of STRONG status does not create a new episode.

## Frozen measurements
For every episode and partition/timeframe record:
- start timestamp and next-open reference price;
- first HEALTHY/WEAKENING timestamp if any;
- first REVERSAL timestamp;
- bars from strong onset to reversal;
- bars from onset to first non-STRONG state;
- survival through 1, 2, 3, 4, 6, 12, 24, 48 bars;
- immediate reversal rates within 1, 2, 3 bars;
- return from next open after onset to next open after reversal;
- MFE and MAE during the episode;
- fraction of episodes that re-enter STRONG after an intermediate state before reversal;
- fraction of episode bars classified STRONG / HEALTHY / WEAKENING.

## Interpretation rule
B23A is evidence for lifecycle persistence only. It does not claim a tradable win rate. A later preregistration may test entry after N causal confirmation bars, but B23A itself will not choose N from performance.

## Guardrails
- No fixed TP.
- No stop optimization.
- No threshold sweep.
- No future information in state detection.
- No result-based edits to this preregistration.
- Live BBC untouched.
