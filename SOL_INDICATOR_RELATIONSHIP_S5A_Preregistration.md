# SOL Indicator Relationship Discovery — Stage 5A Preregistration

**Status:** FROZEN BEFORE STAGE 5A RESULT OBSERVATION  
**Parent:** Stage 2 targets, Stage 3 single-variable findings, Stage 4/4C interaction definitions/results are frozen.  
**Pair:** SOLUSDT USD-M perpetual  
**Live trading:** untouched.

## Objective

Stage 5A asks **temporal ordering** questions:
- does OI expansion/contraction precede taker imbalance, volume expansion, 5m impulse, or breakout?
- do those variables instead move first and OI follow?
- which ordered relationships replicate across DEV 2023–24, 2025, and 2026?

This stage remains observational/predictive. It does not claim structural causality.

## Frozen target and partitions

Primary target remains Stage 2:
- `target_1pct_4h`
- `D = P(LONG first) - P(SHORT first)`

Partitions:
- DEV: 2023-01-01 <= t < 2025-01-01
- VAL1: 2025
- VAL2: 2026 through frozen dataset end

## Frozen state boundaries

Reuse the exact Stage 4 DEV thresholds:
- continuous variables: DEV tertiles LOW / MID / HIGH
- breakout: ZERO / POSITIVE
- 5m impulse:
  - DOWN_IMPULSE <= -0.50%
  - NEUTRAL between -0.50% and +0.50%
  - UP_IMPULSE >= +0.50%

No Stage 5A re-estimation of thresholds.

## 5A1 — Lag atlas

Frozen lags:
- 15 minutes
- 30 minutes
- 60 minutes

For each lag `L`, evaluate prior state at `t-L` against the Stage 2 outcome starting at decision time `t`.

Lagged variables:
1. oi_chg_15m
2. taker_imb_15m
3. quotevol_z_24h
4. impulse5m_prev
5. breakout_up_24h
6. breakout_down_24h

For each variable × lag × bucket report:
- N
- LONG / SHORT / NONE / AMBIGUOUS
- D
- median 4h return
- median 4h max-up / max-down

For continuous variables, report HIGH-minus-LOW `delta-D`.
For impulse, report UP_IMPULSE-minus-DOWN_IMPULSE.
For breakout, POSITIVE-minus-ZERO.

Replication gate for a lagged marginal effect:
- DEV endpoint N >= 200 each
- VAL endpoint N >= 100 each
- |DEV delta-D| >= 5pp
- same sign in both validation partitions
- |validation delta-D| >= 2pp each

## 5A2 — Ordered mechanism motifs

Frozen lead lags:
- 15m
- 30m
- 60m

For each motif, the **lead state is measured at t-L**, while the trigger/current state is measured at `t`.

### OI -> Taker
A1. prior OI HIGH vs LOW, current taker HIGH
A2. prior OI HIGH vs LOW, current taker LOW

### Taker -> OI
B1. prior taker HIGH vs LOW, current OI HIGH
B2. prior taker HIGH vs LOW, current OI LOW

### OI -> Volume
C1. prior OI HIGH vs LOW, current volume-z HIGH

### Volume -> OI
D1. prior volume-z HIGH vs LOW, current OI HIGH
D2. prior volume-z HIGH vs LOW, current OI LOW

### OI -> 5m impulse
E1. prior OI HIGH vs LOW, current UP_IMPULSE
E2. prior OI HIGH vs LOW, current DOWN_IMPULSE

### 5m impulse -> OI
F1. prior UP_IMPULSE vs DOWN_IMPULSE, current OI HIGH
F2. prior UP_IMPULSE vs DOWN_IMPULSE, current OI LOW

### OI -> breakout
G1. prior OI HIGH vs LOW, current breakout_up POSITIVE
G2. prior OI HIGH vs LOW, current breakout_down POSITIVE

### breakout -> OI
H1. prior breakout_up POSITIVE vs ZERO, current OI HIGH
H2. prior breakout_down POSITIVE vs ZERO, current OI LOW

## 5A3 — First-mover comparison

For each mechanism family, compare the strongest **pre-frozen lag rows only as descriptive output**:
- OI -> Taker versus Taker -> OI
- OI -> Volume versus Volume -> OI
- OI -> Impulse versus Impulse -> OI
- OI -> Breakout versus Breakout -> OI

No single best lag is promoted solely from DEV.

A family receives `TEMPORAL_REPLICATION` only if **at least one same fixed lag** (15m, 30m, or 60m) passes in DEV, 2025, and 2026 using the replication gate below.

## Ordered-motif replication gate

For each motif × exact lag:
- DEV contrast endpoint N >= 150 each
- each validation endpoint N >= 75 each
- |DEV delta-D| >= 6pp
- same sign in 2025 and 2026
- |validation delta-D| >= 3pp in each

Pass = `REPLICATED_SEQUENCE`.  
Fail = `WEAK_OR_UNSTABLE`.

A replicated sequence is still not an executable trading rule.

## Guardrails

1. No threshold changes after results.
2. No lag outside 15/30/60m may be added in Stage 5A.
3. Same Stage 2 entry anchor and 4h target are preserved.
4. Stage 5A measures predictive temporal ordering, not causal mechanism.
5. Stage 5B BTC.D / USDT.D remains separate and cannot alter Stage 5A results.
6. Stage 6 market-state naming must be based on replicated patterns rather than narrative labels imposed in advance.

**STAGE5A_FROZEN_BEFORE_RESULTS**
