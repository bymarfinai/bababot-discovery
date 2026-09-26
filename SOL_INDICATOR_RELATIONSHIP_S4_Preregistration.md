# SOL Indicator Relationship Discovery — Stage 4 Preregistration

**Status:** FROZEN BEFORE STAGE 4 RESULT OBSERVATION  
**Parent:** Stage 2 targets + Stage 3 feature definitions/results frozen.  
**Pair:** SOLUSDT USD-M perpetual  
**Live trading:** untouched.

## Stage 4 objective

Map **conditional interactions** between SOL-native features. This stage does not yet create an executable entry rule.

Primary outcome remains:
- `target_1pct_4h`
- directional score `D = P(LONG first) - P(SHORT first)`

## Frozen partitions
- DEV: 2023-01-01 <= t < 2025-01-01
- VAL1: 2025
- VAL2: 2026 through frozen dataset end

Thresholds are learned from DEV only and applied unchanged to both validation partitions.

## 4A — Core pairwise interaction atlas

Continuous features use DEV tertiles: LOW / MID / HIGH.
Breakout uses ZERO / POSITIVE.
Previous completed 5m impulse uses:
- DOWN_IMPULSE: return <= -0.50%
- NEUTRAL: -0.50% < return < +0.50%
- UP_IMPULSE: return >= +0.50%

Frozen pair list:

1. oi_chg_15m × loc_24h
2. oi_chg_15m × dist_high_24h
3. oi_chg_15m × dist_low_24h
4. oi_chg_15m × taker_imb_15m
5. oi_chg_15m × taker_imb_change_1h
6. oi_chg_15m × quotevol_z_24h
7. oi_chg_15m × breakout_up_24h
8. oi_chg_15m × breakout_down_24h
9. oi_chg_15m × funding_z_30
10. oi_chg_1h × loc_24h
11. impulse5m_prev × oi_chg_15m
12. impulse5m_prev × taker_imb_15m
13. impulse5m_prev × quotevol_z_24h

For every cell report:
- N
- LONG / SHORT / NONE / AMBIGUOUS rates
- D
- median 4h return
- median 4h max-up / max-down

## 4B — Frozen mechanism contrasts

Contrasts are defined before results and are not selected post hoc.

A. OI expansion vs contraction at high 24h location:
- OI HIGH + loc HIGH
- OI LOW + loc HIGH

B. OI expansion vs contraction at low 24h location:
- OI HIGH + loc LOW
- OI LOW + loc LOW

C. Positive breakout:
- OI HIGH + breakout_up POSITIVE
- OI LOW + breakout_up POSITIVE

D. Negative breakout:
- OI HIGH + breakout_down POSITIVE
- OI LOW + breakout_down POSITIVE

E. Up 5m impulse:
- UP_IMPULSE + OI HIGH
- UP_IMPULSE + OI LOW

F. Down 5m impulse:
- DOWN_IMPULSE + OI HIGH
- DOWN_IMPULSE + OI LOW

G. Aggressive buying:
- OI HIGH + taker HIGH
- OI LOW + taker HIGH

H. Aggressive selling:
- OI HIGH + taker LOW
- OI LOW + taker LOW

I. Volume expansion:
- OI HIGH + volume-z HIGH
- OI LOW + volume-z HIGH

J. Funding context:
- OI HIGH + funding-z HIGH
- OI LOW + funding-z HIGH
- OI HIGH + funding-z LOW
- OI LOW + funding-z LOW

## Frozen replication flag

For each two-cell contrast:
- DEV endpoint N >= 150 each
- each validation endpoint N >= 75 each
- |delta-D DEV| >= 6 percentage points
- same sign in 2025 and 2026
- |delta-D| >= 3 percentage points in each validation

If all pass: `REPLICATED_CONDITIONAL`.
Otherwise: `WEAK_OR_UNSTABLE`.

This is a research classification, not a deployable-rule promotion.

## Cross-market dominance placement

BTC dominance and USD/USDT dominance are **not executed in Stage 4**.

They are preregistered for:

### Stage 5B — Cross-Market Context & Lead-Lag
Candidate context series:
- BTC.D
- USDT.D (preferred stablecoin-dollar dominance proxy if sourced consistently)
- optional TOTAL / TOTAL2 / TOTAL3 market-cap indices where reproducible historical data exists

Questions:
1. Does a change in BTC.D precede SOL directional expansion?
2. Does rising USDT.D precede SOL downside / risk-off expansion?
3. Does falling USDT.D precede SOL upside / risk-on expansion?
4. Is dominance useful only jointly with SOL OI / price impulse?
5. What lag is informative: 15m, 1h, 4h, 8h, 24h?

Causality rule:
- only dominance observations published/available at or before SOL decision time;
- no forward-nearest alignment;
- source consistency must be documented before any result is accepted.

**STAGE4_FROZEN_BEFORE_RESULTS**
