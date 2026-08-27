# BNB Session-Native Discovery — London M1 Structure — B27EL

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Reset BNB discovery around the pair's own canonical market sessions rather than inheriting BTC-derived clocks. B27EL maps the native **London session structure** first. New York is deliberately deferred to the next milestone.

This milestone is **structural/diagnostic only**. It contains no F85/F15 assumption, no entry, no stop, no target selection, no PnL, no parameter sweep, and no zone-time optimization.

## Instrument and data
- Instrument: Binance USD-M `BNBUSDT` perpetual.
- Raw timeframe: 5m Binance Vision.
- Data interval: `2020-01-01 <= ts < 2026-08-26` UTC, inherited loader coverage gate >=99.5%.
- Partitions remain frozen for auditability:
  - external: 2020-01-01 through 2021-12-31;
  - development: 2022-01-01 through 2024-12-31;
  - reference_validation: 2025-01-01 through 2026-07-29;
  - August 2026 remains diagnostic only.

## London clock — DST aware
All session boundaries are defined in **`Europe/London` local civil time**, then converted to UTC. No fixed UTC hour is used.

For every London-local weekday:
- `pre_London_range`: 00:00 <= local time < 08:00;
- `London_morning_observation`: 08:00 <= local time < 13:00.

The 13:00 local cutoff is chosen before execution to focus on London morning and reduce contamination from the later New York session. It is not optimized from BNB outcomes.

Required audit fields include local date, UTC session-open timestamp, UTC offset, and GMT/BST regime.

## Frozen structural definitions
For each complete session:
1. `H` = highest high of the complete 00:00–08:00 London-local pre-session range.
2. `L` = lowest low of the same range; `R = H-L`, requiring R>0.
3. `UP_BREAK` = first completed 5m candle in 08:00–13:00 with `close > H`.
4. `DOWN_BREAK` = first completed 5m candle in 08:00–13:00 with `close < L`.
5. The chronologically first strict completed-close break owns the session. If no strict break occurs, classify `NO_BREAK`.
6. Breakout information is considered known only when its 5m candle closes. All post-break causal sequence analysis begins on the **next** raw5m bar.

## Boundary retest definitions
For `UP_BREAK`, the broken boundary is H; for `DOWN_BREAK`, it is L.

Starting strictly after the breakout bar:
- `boundary_retest_bar`: UP -> `low <= H`; DOWN -> `high >= L`.
- Consecutive retest bars count as one `retest_episode`.
- `HOLD_RETEST`: first retest contact closes on the breakout side of the boundary (UP close >= H; DOWN close <= L).
- `ACCEPT_BACK_INSIDE`: a completed close returns through the broken boundary (UP close < H; DOWN close > L).
- Also record whether price later reaches the opposite pre-London boundary before 13:00.

No retest condition is an entry rule in B27EL.

## Post-break continuation map
Normalize all movement by pre-London R.

For UP breaks evaluate H+0.10R / +0.20R / +0.30R / +0.50R. For DOWN breaks evaluate L-0.10R / -0.20R / -0.30R / -0.50R.

Report independent reach rates by break side, partition, and DST regime.

Also classify the **first causal event starting on the bar after breakout close** among:
- `DIRECT_E10`: E10 continuation occurs before a boundary retest/acceptance event;
- `BOUNDARY_HOLD_RETEST`: boundary is touched and the bar closes on breakout side before E10;
- `ACCEPT_BACK_INSIDE`: completed close crosses back through boundary before E10;
- `AMBIGUOUS_E10_BOUNDARY_INTERACTION`: same 5m bar contains E10 and boundary interaction, so intrabar ordering is unknowable;
- `TIMEOUT`.

If first event is `BOUNDARY_HOLD_RETEST`, report later E10/E20 reach rates, but do not turn them into rules.

## Required outputs
### Overall / side structure
- complete sessions;
- UP_BREAK / DOWN_BREAK / NO_BREAK counts and rates;
- median minutes from London open to first strict break;
- retest episode distribution 0 / 1 / 2 / 3+;
- first-retest HOLD vs ACCEPT_BACK_INSIDE;
- first causal post-break event distribution;
- E10/E20/E30/E50 reach rates;
- opposite-boundary reach rate.

### Stability
Repeat core metrics for:
- external;
- development;
- reference_validation;
- August diagnostic;
- GMT sessions;
- BST sessions.

## Descriptive labels
These labels summarize structure only; none authorizes a trade.

Per breakout side:
- `DIRECT_CONTINUATION_DOMINANT` if DIRECT_E10 >=50% of strict breaks;
- `HOLD_RETEST_DOMINANT` if BOUNDARY_HOLD_RETEST >=50%;
- `FAILED_BREAK_DOMINANT` if ACCEPT_BACK_INSIDE >=50%;
- otherwise `MIXED_BREAK_SEQUENCE`.

Retest-count label among sessions that reach E20:
- `NO_RETEST_TO_E20_DOMINANT` if >=60% have 0 retest episodes before first E20;
- `ONE_RETEST_TO_E20_DOMINANT` if >=50% have exactly 1;
- `MULTI_RETEST_TO_E20_DOMINANT` if >=50% have >=2;
- otherwise `MIXED_RETEST_TO_E20`.

## Mandatory audits
Execution aborts before persistence if:
1. B27EL was not preregistered first;
2. session boundaries are generated from `Europe/London` local time rather than a fixed UTC hour;
3. any complete pre-London range is not exactly 96 raw5m bars or London morning is not exactly 60 raw5m bars;
4. post-break sequence begins on the breakout bar instead of the next bar;
5. same-bar E10 + boundary interaction is credited with favorable ordering;
6. any entry/PnL/stop/target optimization or time-zone sweep is performed;
7. raw BNB 5m coverage <99.5%;
8. results persist anywhere except branch `bnb-session-native-london-ny`.

**Research only. STOP after B27EL. New York native structure is the next separate milestone, not part of this run.**
