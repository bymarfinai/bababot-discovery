# SOL Indicator Relationship Discovery — Stage 6 Preregistration

**Status:** FROZEN BEFORE STAGE 6 RESULT OBSERVATION  
**Parent evidence:** Stages 2, 3, 4, 4C, 5A, 5B frozen.  
**Purpose:** regime overlay + mutually-exclusive SOL market-state mapping.  
**Research only:** no live BabaBot rule is changed here.

## 1. Frozen outcome and partitions

Primary outcome remains Stage 2:
- `target_1pct_4h` = first-touch race ±1% within 4h from the causal entry anchor.
- Direction score `D = P(LONG first) - P(SHORT first)`.
- Expansion rate = `1 - P(NONE)`; AMBIGUOUS counts as expansion because both barriers were touched, but never as directional success.

Partitions remain:
- DEV = 2023-01-01 through 2024-12-31
- VAL1 = 2025
- VAL2 = 2026 through frozen dataset end.

No thresholds may be selected from 2025/2026.

## 2. Frozen regime layer

Stage 6 uses the canonical SOL regime research state already frozen in the separate regime-detector research:

### BULL — V1.5 adaptive Bull
At a completed 1H bar:
- compute `rv8`, `rv24`, `ATR14%`, and distance from 8H high;
- causal percentile history = previous 720 completed 1H observations, excluding current;
- BULL candidate if at least 2 of `rv8 / rv24 / ATR14%` are at or above their rolling 85th percentile;
- and distance from 8H high is at or below its rolling 25th percentile.

### BEAR — frozen V1 fallback
- `accel4v12 >= 1.101215540095295`
- `close_loc >= 0.6260779194779318`

### SIDEWAYS — frozen V1
- `rv8 < 0.47186330933162923`
- `ATR14% < 0.9798115352248504`

If BULL and BEAR both fire => TRANSITION.  
Otherwise insufficient directional evidence => TRANSITION.

Exact V1 feature formulas are copied from the frozen canonical implementation:
- `rv8/rv24` = population SD of 1H log returns ×100;
- `ATR14%` = simple mean of the latest 14 true ranges / close ×100;
- `distHigh8 = close / max(high last 8 completed 1H bars) - 1`, in percent;
- `accel4v12 = ret4 - ret12/3`;
- `close_loc = 2*(close-low)/(high-low)-1`.

Regime availability timestamp = 1H bar close.  
At a 15m decision time, Stage 6 uses only the most recently completed 1H regime state.

## 3. Frozen Stage-4 microstate buckets

Stage 6 reuses the exact DEV thresholds already frozen in Stage 4 for:
- `oi_chg_15m` => LOW / MID / HIGH
- `loc_24h` => LOW / MID / HIGH
- `taker_imb_15m` => LOW / MID / HIGH
- `quotevol_z_24h` => LOW / MID / HIGH
- `breakout_up_24h` => POSITIVE / ZERO
- `breakout_down_24h` => POSITIVE / ZERO
- previous completed 5m impulse:
  - UP_IMPULSE >= +0.50%
  - DOWN_IMPULSE <= -0.50%
  - otherwise NEUTRAL.

No new bucket threshold is learned in Stage 6.

BTC.D and USDT.D are excluded from state definitions because Stage 5B found no replicated incremental information beyond SOL-native state.

Funding is not a state splitter because its standalone orientation was unstable and Stage 4 showed the OI contrast persisted in both high- and low-funding contexts.

## 4. Orthogonal state tags

At every 15m decision:
- `OI = EXPAND / MID / CONTRACT` from HIGH / MID / LOW `oi_chg_15m`;
- `FLOW = BUY / MID / SELL` from HIGH / MID / LOW taker bucket;
- `VOLUME = HIGH / OTHER`;
- `LOCATION = HIGH / MID / LOW`;
- `PRICE_EVENT_UP = UP_IMPULSE OR breakout_up_24h POSITIVE`;
- `PRICE_EVENT_DOWN = DOWN_IMPULSE OR breakout_down_24h POSITIVE`;
- simultaneous UP and DOWN event => EVENT_CONFLICT;
- `POST_DOWNBREAK_OI_CONTRACT_30M` = down-breakout POSITIVE exactly 30m earlier AND current OI=CONTRACT. This is the one Stage-5A sequence that replicated.

## 5. Mutually-exclusive market archetype

Precedence is frozen before outcome inspection:

1. EVENT_CONFLICT
2. POST_BREAKDOWN_UNWIND_30M
3. UP_POSITION_BUILD = PRICE_EVENT_UP + OI EXPAND
4. UP_UNWIND_LIKE = PRICE_EVENT_UP + OI CONTRACT
5. DOWN_POSITION_BUILD = PRICE_EVENT_DOWN + OI EXPAND
6. DOWN_UNWIND_LIKE = PRICE_EVENT_DOWN + OI CONTRACT
7. HIGHLOC_BUY_BUILD = no price event + LOCATION HIGH + FLOW BUY + OI EXPAND
8. HIGHLOC_BUY_EXHAUSTION_LIKE = no price event + LOCATION HIGH + FLOW BUY + OI CONTRACT
9. HIGHLOC_SELL_ABSORPTION_LIKE = no price event + LOCATION HIGH + FLOW SELL + OI EXPAND
10. HIGHLOC_SELL_UNWIND_LIKE = no price event + LOCATION HIGH + FLOW SELL + OI CONTRACT
11. PRESSURE_BUILD = no prior archetype + VOLUME HIGH + OI EXPAND
12. DELEVERAGING = no prior archetype + VOLUME HIGH + OI CONTRACT
13. NEUTRAL_TRANSITION = everything else.

Names ending in `_LIKE` are mechanism hypotheses, not causal claims.

## 6. Stage 6A — regime baseline

For each regime × partition report:
- N
- LONG / SHORT / NONE / AMBIGUOUS
- D
- expansion rate
- median forward 4h return
- median max-up / max-down 4h.

No regime threshold is adjusted from these results.

## 7. Stage 6B — archetype outcome map

For each archetype × partition report the same metrics.

A market archetype is tagged `REPLICATED_DIRECTIONAL_STATE` only if:
- DEV N >= 150, 2025 N >= 75, 2026 N >= 75;
- |DEV D| >= 8 percentage points;
- the sign of D is identical in DEV, 2025, 2026;
- |D| >= 4 percentage points in each validation partition.

A market archetype is tagged `REPLICATED_EXPANSION_STATE` only if:
- same support gate;
- expansion rate exceeds the partition-wide baseline by >=5pp in DEV;
- and >=3pp in both 2025 and 2026.

Both tags may coexist.

## 8. Stage 6C — regime × archetype cells

For every regime/archetype cell:
- report the same outcome metrics.

A cell is tagged `STABLE_DIRECTIONAL_CELL` only if:
- DEV N >= 100, 2025 N >= 50, 2026 N >= 50;
- |DEV D| >= 10pp;
- same D sign in all three partitions;
- |D| >= 5pp in each validation partition.

No cell becomes a trading rule in Stage 6.

## 9. Stage 6D — lifecycle transition atlas

For every non-neutral archetype, purely descriptively measure:
- state persistence at +15m and +30m;
- transition share to each other archetype at +15m and +30m.

This transition atlas does not use future price outcome and has no winner-selection gate.

## 10. Guardrails

- Stage 6 maps states; it does not choose LONG/SHORT entries.
- Stage 7 alone may convert replicated states into candidate signal logic.
- No TP/SL, fee, frequency, cooldown, or one-position economics are optimized here.
- No semantic label such as liquidation, absorption, or exhaustion is treated as proven market causality.
- Dominance variables remain context-only and are not reintroduced after failing Stage 5B incremental replication.

**STAGE6_FROZEN_BEFORE_RESULTS**
