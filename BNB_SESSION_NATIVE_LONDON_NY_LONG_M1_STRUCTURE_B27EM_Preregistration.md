# B27EM — BNB Session-Native London→New York LONG M1 Structural Baseline — Preregistration

## Purpose
Establish the native BNB LONG structural baseline using canonical London-to-New-York session anchors before any BNB-specific zone-time search, entry rule, stop, target, or PnL test.

## Branch / lineage
- Repository: `bymarfinai/bababot-discovery`
- Branch: `bnb-session-native-london-ny`
- Parent state: B27EL London anatomy complete.
- `main` must not be written by this milestone.

## Frozen market / data
- Symbol: `BNBUSDT`
- Raw Binance Vision futures UM 5m OHLC.
- Use the same raw-data loader and partitions as the prior BNB transfer/session milestones.
- Required raw coverage >= 99.5% over the actual available BNB span.
- A session is included only when the full reference and execution windows are present; any internal missing 5m bar inside an otherwise eligible session is an execution error.

## Canonical session clocks — DST-aware
No fixed UTC clock is assumed.

For each eligible weekday calendar date:
- `LONDON_OPEN` = 08:00 in `Europe/London`.
- `NY_OPEN` = 09:30 in `America/New_York` on the same local calendar date.
- Reference range = `[LONDON_OPEN, NY_OPEN)`.
- Execution / observation = `[NY_OPEN, 16:00 America/New_York)`.

Because London and New York change DST on different dates, reference duration is allowed to vary causally according to the two IANA zones. The expected normal duration is 6h30; DST-mismatch weeks can produce 5h30. Duration regime is recorded, not optimized.

## Frozen LONG structure
Let `H` = reference high, `L` = reference low, `R = H-L`.

During the post-NY-open execution window, inspect only the LONG / upper-boundary sequence:

1. `SEEK_K1_HIGH`
   - A High visit episode is a completed 5m bar with `high >= H` and `close <= H`.
   - A Low visit episode is a completed 5m bar with `low <= L` and `close >= L`.
   - Visit episodes are counted only on transition into the touching state, so consecutive touching bars form one visit episode.
   - LONG K1 OPP0 qualifies only when the first High visit episode occurs while Low visit count is still zero.
   - If a completed bar closes above H or below L before K1 qualification, the session terminates as `BREAK_BEFORE_K1`.
   - Same-bar High+Low interaction before qualification is `AMBIGUOUS_BOTH_BOUNDARIES`.

2. `K1_EPISODE`
   - Consecutive bars touching H with `close <= H` remain the same K1 episode.
   - The first completed bar that no longer touches H is the causal leave bar; leave is only knowable at that bar close.
   - A close outside the reference range during the K1 episode terminates the sequence without causal leave.

3. `AFTER_LEAVE`
   - `H2_ARRIVAL`: first later bar with `high >= H`.
   - `OPPOSITE_BREAK_BEFORE_H2`: first later completed bar with `close < L`.
   - If both occur on the same bar, classify `AMBIGUOUS_H2_VS_OPPOSITE_BREAK` and do not credit as favorable.
   - If neither occurs by NY cash close, classify `NO_H2_BY_END`.

No F85/F35, no entry price, no order, no stop, no target, no PnL.

## Frozen outputs
For pooled-major, each major partition, and each clock regime:
- complete sessions
- reference duration and regime
- LONG K1 OPP0 count / rate
- causal leave count / rate
- H2 arrival count / rate from causal leaves
- opposite-break count
- ambiguous count
- no-H2 count
- resolved H2 share = H2 / (H2 + opposite break), descriptive only
- median minutes from causal leave to H2

Clock regimes:
- `NORMAL_6H30`
- `DST_MISMATCH_5H30`
- any unexpected reference duration must be reported explicitly and must not be silently pooled.

## Structural labels — descriptive, not strategy gates
- `STRONG_HIGH_REVISIT` if pooled-major H2 rate from causal leaves >= 75%.
- `MODERATE_HIGH_REVISIT` if 65% <= rate < 75%.
- `WEAK_HIGH_REVISIT` otherwise.

Stability is reported by partition and clock regime. No source/time-zone optimization is allowed in B27EM.

## Stop condition
B27EM ends after the LONG London→New York structural baseline is persisted. Do not automatically run SHORT, entry discovery, zone-time search, economics, forward shadow, or live integration.
