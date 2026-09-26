# SOL Indicator Relationship Discovery — Stage 5B Preregistration

**Status:** FROZEN BEFORE STAGE 5B RESULT OBSERVATION  
**Parent:** Stages 2, 3, 4, 4C, and 5A frozen.  
**Pair:** SOLUSDT USD-M perpetual  
**Cross-market context:** TradingView CRYPTOCAP dominance indices  
**Live trading:** untouched.

## Objective

Stage 5B asks whether BTC and USDT dominance carry predictive cross-market context for subsequent SOL direction/expansion, and whether that context changes the meaning of SOL OI and 5m impulse states.

This stage is observational/predictive, not causal.

## Source

Primary series:
- `CRYPTOCAP:BTC.D`
- `CRYPTOCAP:USDT.D`

Source resolution:
- 15-minute historical bars.

Dominance values use TradingView CRYPTOCAP definitions. No synthetic proxy may silently replace a missing dominance series.

If a source cannot provide adequate 2023–2026 intraday history, that series is marked SOURCE_FAIL and is excluded rather than approximated.

## Frozen partitions and SOL target

- DEV: 2023-01-01 <= t < 2025-01-01
- VAL1: 2025
- VAL2: 2026 through frozen SOL dataset end
- Primary outcome: Stage 2 `target_1pct_4h`
- Directional score: `D = P(LONG first) - P(SHORT first)`

## Source audit acceptance

For each dominance series:
- usable range must overlap all three partitions;
- coverage on the SOL 15m decision grid must be >= 95% after causal backward alignment;
- maximum accepted age of last observation = 30 minutes;
- no future-nearest matching.

If either BTC.D or USDT.D fails, report it independently; the other series may continue.

## 5B1 — Dominance change features

For each accepted dominance series, calculate close-to-close change over:
- 15m
- 1h
- 4h
- 8h
- 24h

Feature names:
- `btcd_chg_15m/1h/4h/8h/24h`
- `usdtd_chg_15m/1h/4h/8h/24h`

All changes use only dominance observations known at decision time.

For each feature:
- derive DEV tertiles LOW / MID / HIGH;
- freeze thresholds;
- apply unchanged to 2025 and 2026.

Report by bucket:
- N
- LONG / SHORT / NONE / AMBIGUOUS
- D
- median 4h forward return
- median 4h max-up / max-down.

Marginal replication gate:
- DEV endpoints >= 200 each
- validation endpoints >= 100 each
- |DEV HIGH-minus-LOW delta-D| >= 5pp
- same sign in 2025 and 2026
- |validation delta-D| >= 2pp each.

## 5B2 — Dominance × SOL OI context

Reuse exact Stage 5A/Stage 4 DEV tertiles for `oi_chg_15m`.

For every dominance change window (15m/1h/4h/8h/24h), test:

### BTC.D
- BTC.D HIGH + OI HIGH vs BTC.D HIGH + OI LOW
- BTC.D LOW + OI HIGH vs BTC.D LOW + OI LOW

### USDT.D
- USDT.D HIGH + OI HIGH vs USDT.D HIGH + OI LOW
- USDT.D LOW + OI HIGH vs USDT.D LOW + OI LOW

Conditional replication gate:
- DEV endpoints >= 150
- validation endpoints >= 75
- |DEV delta-D| >= 6pp
- same sign 2025 and 2026
- |validation delta-D| >= 3pp each.

## 5B3 — Dominance × SOL 5m impulse

Reuse frozen impulse:
- UP_IMPULSE >= +0.50%
- DOWN_IMPULSE <= -0.50%

For every dominance change window, test:

- dominance HIGH + UP_IMPULSE vs dominance LOW + UP_IMPULSE
- dominance HIGH + DOWN_IMPULSE vs dominance LOW + DOWN_IMPULSE

Run independently for BTC.D and USDT.D.

Same conditional replication gate as 5B2.

## 5B4 — Cross-market lead timing

To avoid lag fishing, fixed prior lags are:
- 15m
- 60m
- 240m (4h)

For each dominance 1h change state at `t-L`, compare HIGH vs LOW against SOL Stage-2 outcome at `t`.

Run for BTC.D and USDT.D.

A lagged dominance effect passes only if the exact same lag satisfies the marginal replication gate in DEV, 2025, and 2026.

## Interpretation constraints

- Rising BTC.D is not assumed bearish for SOL.
- Rising USDT.D is not assumed risk-off for SOL.
- Falling dominance is not assumed bullish.
- Results determine sign empirically.
- A dominance effect is not promoted as a trading rule in Stage 5B.
- TOTAL/TOTAL2/TOTAL3 are deferred unless BTC.D/USDT.D add replicating information.

**STAGE5B_FROZEN_BEFORE_RESULTS**
