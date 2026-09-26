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

### 5B2b — Incremental dominance after holding OI fixed

For every dominance change window, also test:
- within OI HIGH: dominance HIGH vs dominance LOW
- within OI LOW: dominance HIGH vs dominance LOW

This is the direct test of whether cross-market dominance adds information beyond the already-strong SOL OI state.

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


## Source-feasibility amendment before analytical results

The anonymous TradingView 15m full-history traversal returned only recent data and rejected deeper history before any SOL outcome analysis was run.

Therefore Stage 5B uses the following transparent fallback:
- primary source symbols remain exactly CRYPTOCAP:BTC.D and CRYPTOCAP:USDT.D;
- source resolution changes from 15m to **1h** to obtain full 2023–2026 coverage;
- the preregistered **15m dominance-change feature is marked UNAVAILABLE and is not approximated**;
- retained change windows: 1h / 4h / 8h / 24h;
- causal availability time = 1h bar end;
- accepted age of last completed dominance observation on the 15m SOL decision grid <= 60 minutes;
- 5B4 lead lags retained at 60m and 240m; the 15m dominance lead-lag is marked UNAVAILABLE because the source cannot resolve a distinct 15m state historically.

Targets, DEV/validation partitions, tertile-learning rule, and all replication gates remain unchanged.

**S5B_SOURCE_AMENDMENT_FROZEN_BEFORE_ANALYTICAL_RESULTS**
