# B27BF — BTC 24H Adaptive Regime Router Audit — Preregistration

## Question
Can the existing causal 4H regime state be used as a **24/7 adaptive playbook router**—BULL activates the frozen LONG playbook, BEAR activates the frozen SHORT playbook, SIDEWAYS stays flat—without any Asia/London/New-York clock gate?

B27BE remains a frozen structural baseline and is not modified or replaced by B27BF.

## Frozen data and clock semantics
- Existing BTCUSDT 5m source: 698,112 rows / 100% coverage expected.
- Existing external / development / reference_validation / August partitions.
- All seven calendar days included.
- Full day covered continuously by sequential completed 4H ranges. UTC 4H boundaries are detector/range refresh timestamps, **not preferred trading hours**.
- At each 4H boundary, the immediately previous completed 4H H/L becomes the frozen liquidity range for the next 4H observation interval.
- Reuse the exact B27BE/B27AG causal 4H regime semantics. A state is available only when its source 4H bar has fully completed.
- No Asia/London/New-York/session label is used for eligibility.

## Adaptive router — frozen before results
- `BULL` -> only the frozen LONG playbook may open a new position.
- `BEAR` -> only the frozen SHORT playbook may open a new position.
- `SIDEWAYS` -> no new position in B27BF v1.
- A new regime/range state affects only **new entries**. An already-open position is managed by its frozen exit logic until exit or the end of its current 4H observation interval.
- At most one routed position may be opened per 4H observation interval.
- No overlapping routed positions.

## Frozen BULL LONG playbook
This is the existing B27W/B27AA/B27AC LONG lineage translated to the rolling previous-4H range without changing its fractions:
1. Frozen range `L < H`, `R=H-L`.
2. First distinct High visit K1 with OPP0: `high>=H` and `close<=H`, with no prior distinct Low visit and no prior strict close break.
3. Collapse consecutive High-touch bars into one visit episode.
4. Require a causal leave from High visit #1. Entry search begins on the next 5m bar after the leave bar completes.
5. Frozen pullback level `F85=L+0.85R`.
6. F85 touch bar must occur before H2 and before strict opposite break. SAME_BAR confirmation requires the F85-touch bar to close strictly above F85; entry is the next 5m open and must remain below H.
7. Frozen pre-E20 invalidation is completed 5m close below `F35=L+0.35R`, exited at actual close.
8. Frozen activation `E20_UP=H+0.20R`. Intrabar E20 touch precedes same-bar later close invalidation.
9. After E20, 100% position remains open. From the next bar E20 is the resting profit floor; strict causal 3-bar pivot lows above the floor may ratchet it upward, never downward.
10. If open <= floor exit at actual open; otherwise if low <= floor exit at floor. No upper fixed TP.
11. If still open at observation-interval end, exit at the exact next 4H boundary open.

## Frozen BEAR SHORT playbook
This is the current B27AY/B27BC leading SHORT lineage translated to the rolling previous-4H range without changing its fractions:
1. Frozen range `L < H`, `R=H-L`.
2. First distinct Low visit K1 with OPP0: `low<=L` and `close>=L`, with no prior distinct High visit and no prior strict close break.
3. Collapse consecutive Low-touch bars into one visit episode.
4. Require causal leave from Low visit #1.
5. Require a distinct valid Low retest #2 before strict breakdown `<L`, opposite break `>H`, or interval end.
6. Collapse retest #2 episode and require a causal leave; entry eligibility starts next 5m bar.
7. Frozen entry `F15=L+0.15R`; fill must occur strictly after leave #2 and before retest #3, strict breakdown, opposite break, or interval end.
8. Frozen hard stop distance is `D30=0.30R` above actual F15 entry, active intrabar from fill bar. If stop and E20 are both touched in the same 5m bar, stop wins conservatively because intrabar ordering is unknown.
9. Frozen activation `E20_DOWN=L-0.20R`; fill bar cannot activate.
10. After E20, 100% position remains open. From the next bar E20 becomes the resting profit ceiling; strict causal 3-bar pivot highs below the ceiling may ratchet it downward, never upward.
11. If open >= ceiling exit at actual open; otherwise if high >= ceiling exit at ceiling. No lower fixed TP.
12. If still open at observation-interval end, exit at the exact next 4H boundary open.

## Counterfactual diagnostics
For attribution only, simulate the exact LONG playbook and exact SHORT playbook on every eligible 4H block irrespective of regime. Report economics by actual causal regime. These diagnostics do not change router eligibility.

## Costs and sizing
- $500 notional per trade.
- $0.40 round-trip fee per completed trade, consistent with current research lineage.
- No leverage-dependent PnL amplification is introduced in this audit.

## Outputs
Per major partition, regime, side, and routed aggregate report:
- complete 4H blocks;
- setup count / executed trades;
- WR;
- PF;
- expectancy per trade;
- total PnL;
- E20 activation rate;
- exit-reason counts;
- trades per week diagnostic.

Report three aggregates:
1. `ROUTER`: BULL LONG + BEAR SHORT only; SIDEWAYS flat.
2. `ALL_LONG_DIAGNOSTIC`: same LONG playbook irrespective regime.
3. `ALL_SHORT_DIAGNOSTIC`: same SHORT playbook irrespective regime.

## Frozen support gate
Call the adaptive router `SUPPORTED` only if:
- each major partition has >=30 routed trades;
- each major partition expectancy >=0 and PF >=1.0;
- pooled-major expectancy >0 and PF >=1.20;
- pooled-major router total PnL > 0.

Otherwise verdict = `NOT_SUPPORTED`. No regime/state, fraction, stop, E20, confirmation, pivot, or clock threshold may be changed after seeing results.

## Mandatory assertions
1. B27BE source result remains present and unchanged.
2. 698,112-row / 100% source reproduction.
3. Regime availability timestamp <= observation start for every block.
4. Previous-4H range is complete and frozen before observation starts.
5. No session labels enter eligibility.
6. LONG entries can execute only when router state=BULL; SHORT only when state=BEAR; SIDEWAYS opens zero routed positions.
7. Counterfactual all-regime diagnostics are stored separately from routed trades.
8. Synthetic LONG and SHORT paths verify causal leave, next-bar entry, E20 activation, hard/close invalidation, runner ratchet, and interval-end exit.
9. No live BBC file or live trading rule is modified.

Research only. Live BBC unchanged.
