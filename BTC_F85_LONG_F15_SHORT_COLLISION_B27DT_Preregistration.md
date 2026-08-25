# B27DT — BTC F85 LONG + F15 SHORT Collision / Portfolio Interference Audit — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Measure whether the most interesting B27DR F15 SHORT clock habitats can be added to the existing B27DQ F85 LONG operating portfolio without materially displacing or degrading LONG trades.

This is an **exploratory portfolio-interference audit** because the six SHORT clocks were chosen after inspection of B27DR historical results. It is not pristine unseen OOS evidence and does not authorize live deployment.

## Frozen LONG control
Use the exact B27DQ live-executable F85 LONG research portfolio and its existing four-zone policy:
- ALT_0330
- RAW_0530
- LONDON
- RAW_2330

Use B27DQ's exact candidate stream, zone filters, exit model, fee/notional, partitions, and chronological one-BTC-position semantics.

Before interpreting SHORT interference, reproduce the persisted B27DQ pooled-major control approximately:
- accepted N = 227
- WR = 72.2%
- PF = 2.25
- net = $289.76
- max loss streak = 3

## Frozen SHORT candidates
Use exact B27DR SAME_BAR_REJECTION + fixed E20_DOWN economics with no parameter changes.

Test these six already-observed clock placements individually and as one six-clock basket:

1. `SHORT_2000`: reference 20:00 UTC -> execution 01:30-08:00 UTC
2. `SHORT_0430`: reference 04:30 UTC -> execution 10:00-16:30 UTC
3. `SHORT_0330`: reference 03:30 UTC -> execution 09:00-15:30 UTC
4. `SHORT_0300`: reference 03:00 UTC -> execution 08:30-15:00 UTC
5. `SHORT_2100`: reference 21:00 UTC -> execution 02:30-09:00 UTC
6. `SHORT_0000`: reference 00:00 UTC -> execution 05:30-12:00 UTC

The final `SHORT6_BASKET` contains all six clocks without re-ranking after collision results are seen.

No F15/F65/E20_DOWN, confirmation, timeframe, reference duration, execution duration, fee, sizing, regime, or candle filter may change in B27DT.

## Position interval semantics
For both directions a position occupies `[entry_ts, exit_ts)`.
- An entry exactly at an existing position's exit timestamp is allowed.
- SHORT exit timestamp is reconstructed from B27DR `entry_start + fixed_hold_minutes`.
- LONG timestamps and PnL are taken from the recomputed B27DQ candidate stream.

## Scenario A — LONG_PROTECTED
Purpose: answer whether a SHORT clock can be added **without changing any accepted B27DQ LONG trade**.

1. Reproduce the accepted B27DQ LONG portfolio first.
2. A SHORT candidate is blocked by LONG if its holding interval overlaps any accepted B27DQ LONG interval in the same partition.
3. Remaining SHORT candidates are then chronologically locked against one another using one BTC position at a time.
4. Every baseline LONG remains accepted exactly as in B27DQ.

Report per clock and basket:
- standalone SHORT N / WR / PF / net;
- SHORT candidates blocked by LONG;
- SHORT candidates blocked by another accepted SHORT;
- accepted incremental SHORT N / WR / PF / net;
- combined LONG + incremental SHORT net;
- incremental net versus B27DQ control.

## Scenario B — FIRST_SIGNAL_WINS
Purpose: measure true directional competition if LONG and SHORT are peers.

1. Merge the **raw B27DQ LONG candidate stream** and selected B27DR SHORT candidate stream.
2. Sort chronologically by entry timestamp.
3. One BTC position at a time; a new candidate is accepted only if its entry is at or after the active position exit.
4. Exact entry-timestamp ties are resolved **LONG first**, then SHORT clock minute ascending as deterministic tie-break.
5. Once accepted, direction does not flip early merely because an opposite candidate appears.

Report:
- total accepted N / WR / PF / net;
- accepted LONG N / WR / net;
- accepted SHORT N / WR / net;
- baseline LONG trades displaced versus B27DQ;
- baseline LONG net lost from displaced trades;
- net delta versus B27DQ control;
- directional collision counts.

## Partitions
Use the same B27DQ partitions:
- external
- development
- reference_validation
- august

Primary comparison is `POOLED_MAJOR = external + development + reference_validation`. August is reported separately and is not used to promote a candidate.

## Interpretation labels
For each clock/basket, classify mechanically:

- `ZERO_LONG_INTERFERENCE` if LONG_PROTECTED accepts incremental SHORT trades with positive net and, by construction, no LONG displacement.
- `FIRST_SIGNAL_ADDS_WITHOUT_LONG_DAMAGE` if FIRST_SIGNAL_WINS has combined net > B27DQ, accepted LONG net >= B27DQ LONG net, and displaced baseline LONG count = 0.
- `FIRST_SIGNAL_ADDS_WITH_LONG_DISPLACEMENT` if combined net > B27DQ but at least one baseline LONG is displaced.
- `PORTFOLIO_DEGRADES` if FIRST_SIGNAL_WINS combined net <= B27DQ.

These labels describe historical portfolio interaction only, not live readiness.

## Guardrails
- Do not change live BBC.
- Do not modify B27DQ or B27DR result artifacts.
- Do not optimize the SHORT clock set after B27DT results.
- Any follow-up clock pruning, arbitration policy, or directional router requires a new experiment ID.

Research only; live BBC unchanged.
