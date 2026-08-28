# B27EO Preregistration — BNB Session-Native London→New York LONG K1→H2 Entry Discovery

## Objective
Discover a causal LONG entry event that occurs after the B27EM causal K1 leave and before H2, using only the frozen B27EM development partition. This milestone is entry-location/confirmation discovery only.

## Frozen upstream structure
- Symbol/timeframe: BNBUSDT raw 5m.
- Reference: 08:00 Europe/London → 09:30 America/New_York, DST-aware.
- Execution: 09:30 → 16:00 America/New_York.
- H/L/R and K1/leave/H2 definitions are exactly B27EM.
- Discovery population: development partition only, 2022-01-01 <= NY open < 2025-01-01.
- Expected causal leaves reproduced from B27EM: 97; expected H2 terminals: 76; expected non-H2: 21.
- External, reference_validation and August are forbidden for candidate selection/ranking.

## Causality contract
- `leave_ts` is the completed-bar timestamp at which B27EM knows the first bar outside the K1 high-touch episode has completed.
- No entry may use any OHLC from the leave bar itself after its close to claim an earlier fill.
- Candidate entry signals are formed only from bars starting at or after `leave_ts` and must be known at a completed 5m close; fill is the next 5m bar open unless candidate E0 explicitly uses the first executable bar open at `leave_ts`.
- A candidate is invalid if H2 or opposite-break is already known before its signal/fill.
- On a confirmation bar, if `high >= H` (H2) or `close < L` (opposite break), terminal ownership wins and no entry is emitted from that bar.
- No same-bar ordering assumption between low/high is used for eligibility.

## Predeclared candidate families
All levels are expressed relative to H and R, where Fxx = L + xx/100 * R.

1. **E0_NEXT_OPEN** — buy the first executable 5m bar open at `leave_ts` with no further confirmation, provided open is strictly inside `(L, H)`.
2. **E1_FIRST_BULL_CLOSE** — first post-leave completed bar with `close > open` and `close < H`; enter next bar open.
3. **E2_F95_RECLAIM** — first completed post-leave bar that trades at/below F95 and closes strictly above F95, while terminal has not occurred; enter next bar open.
4. **E3_F90_RECLAIM** — same rule at F90.
5. **E4_F85_RECLAIM** — same rule at F85; frozen BTC-style benchmark.
6. **E5_MICRO_HL_BULL** — first completed post-leave bar after at least one prior post-leave completed bar where current low > previous low, current close > previous close, and current close > current open; enter next bar open.

For E1–E5, the next-bar fill itself must occur before NY close and before a terminal event has already been established. Fill open must be strictly inside `(L, H)`; otherwise candidate is `NO_VALID_FILL`.

## Measurements per candidate
- eligible fills / 97 causal leaves
- H2 after fill count and rate
- non-H2 after fill count
- capture rate among the 76 upstream H2 sessions
- median minutes leave→entry
- median minutes entry→H2 for wins
- entry location normalized as `(H-entry_px)/R`
- post-entry MAE to the low before H2/opposite/end, normalized by R, terminal candle excluded
- maximum and percentile summaries as descriptive diagnostics only

## Ranking contract
B27EO will not call any candidate a profitable strategy. Candidates are descriptively ranked by:
1. H2-after-entry rate,
2. then H2 winner capture rate,
3. then earlier median leave→entry.
No TP, SL, fees, PnL or economics are allowed in B27EO.

## Stop rule
B27EO ends after development-only candidate comparison and descriptive ranking. No validation partition reveal, threshold tuning, TP/SL, economics, H3, breakout-retest, SHORT, or live integration.