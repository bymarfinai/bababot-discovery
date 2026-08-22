# B27AV — BTC London→NY SHORT F15 Failure-Stage Decomposition — Preregistration

## Question
Where does the loss in the frozen B27AT E20 full-position hybrid SHORT path concentrate before E20 activation?

## Frozen sources
- B27AT exact `E20` trade rows only.
- B27AM exact F15 post-H2 path identities/timestamps.
- Major partitions: `external`, `development`, `reference_validation`; `august` is reported separately.

No new market rule is created in B27AV.

## Identity/audit requirements before attribution
1. B27AT E20 rows must reproduce 164 total trades and 163 pooled-major trades.
2. Pooled-major realized B27AT E20 hybrid PnL must reproduce exactly within floating tolerance.
3. Pooled-major E20 activated/non-activated counts must reproduce 92 / 71.
4. B27AT and B27AM must join one-to-one on frozen trade identity (`partition`, `signal_ts`, F15 fill-bar timestamp).
5. Every E20-activated trade must have frozen H2 reached no later than its activated path.

If any assertion fails, no attribution may be interpreted.

## Frozen causal stage buckets
For each frozen E20 trade, milestones are evaluated no later than its **actual B27AT exit timestamp**. Future session events after the trade has exited do not move the trade into a healthier causal bucket.

1. `PRE_H2_FAILURE`
   - E20 did not activate; and
   - frozen H2 had not occurred before the actual exit.

2. `H2_NO_ACCEPTANCE`
   - E20 did not activate;
   - H2 occurred before exit; and
   - no strict completed 5m close `< L` was known by the actual exit timestamp.

3. `ACCEPTED_NO_E20`
   - E20 did not activate;
   - H2 occurred before exit; and
   - strict completed 5m close `< L` was known by exit; but
   - E20 did not activate before exit.

4. `E20_ACTIVATED`
   - frozen B27AT E20 activation occurred; this is the healthy control bucket.

H2 is an intrabar liquidity-touch milestone represented by its frozen raw 5m bar start. Completed-close acceptance is known at `first_close_break_ts` (bar close timestamp).

## Frozen diagnostics
Report by pooled-major and by partition:
- N, WR, PF, expectancy/trade, total PnL, mean win, mean loss;
- exit-reason mix (`PRE_ACT_CLOSE_INVALIDATION_F65`, session end, profit ceiling/gap);
- share of non-activated PnL drag by failure-stage bucket;
- eventual same-session H2 / acceptance after exit, reported only as a diagnostic of late recovery and never used to reclassify the causal bucket.

Also report a stage-flow count for pooled-major:
`F15 fill → H2 before exit → acceptance by exit → E20 activation`.

## Interpretation rule
This is attribution only. No threshold, filter, stop, entry, TP, regime, candle pattern, or runner parameter may be selected or promoted from B27AV.

Research only. Live BBC remains unchanged.
