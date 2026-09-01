# ETH B27DX — S4 Global One-Position Portfolio Lock — Preregistration

## Purpose
Convert the S3C deterministic joint-geometry representative into an executable ETH LONG portfolio across the frozen ETH-native clock set and measure true non-overlapping economics.

S4 is a portfolio-composition test. It does not tune geometry.

## Frozen representative from S3C
- reference: **R300**;
- execution horizon: **X360**;
- entry: **F75**;
- target: **E25**;
- completed-close invalidation: **F20**;
- execution clocks: **05:00, 09:00, 10:00, 16:00 UTC**;
- side: LONG only.

The representative was selected by the preregistered S3C structural-medoid rule, not by performance ranking.

## Frozen causal semantics
- exact B27DX corrected signal grammar;
- completed 5m bars only;
- K1 OPP0;
- completed causal leave;
- first eligible pre-terminal retrace fill;
- no future veto/look-ahead;
- target has the same within-bar priority as the frozen scorer;
- close invalidation uses the completed bar close;
- time exit uses execution-end open.

For portfolio occupancy, target or close-invalidation exits unlock the portfolio only at the **end of the completed 5m exit bar**. This is conservative and avoids assuming unknown intrabar ordering. Time exits unlock at the execution-end timestamp.

## Candidate parity gate
Before portfolio results may be interpreted, the trade-detail reconstruction must exactly reproduce the frozen scorer for every clock × major partition at 0 bps on:
- trade count;
- wins;
- WR;
- PF;
- net PnL.

Any parity mismatch invalidates S4.

## Global one-position lock
Within each partition:
1. sort all candidate trades by entry-bar timestamp;
2. when flat, accept the earliest candidate;
3. while a position is open, skip later candidates with entry timestamp before the accepted trade's exit timestamp;
4. a new candidate is eligible at or after the prior exit timestamp.

### Exact entry-time tie rule
When multiple clocks produce candidates on the exact same 5m entry-bar timestamp, choose the candidate with the **latest execution-start timestamp** (freshest active structural range). Remaining ties use execution clock ascending.

This tie rule is causal, fixed before results, and does not use performance.

## Economics
- notional: **$500**;
- round-trip fee: **$0.40**;
- primary: 0 bps;
- execution stress: **5 bps**, using the frozen scorer convention (entry worsened by 5 bps; non-target exits worsened by 5 bps; fixed target price unchanged).

## Reporting
Report for External, Development, Reference Validation, and Pooled Major:
- candidates / accepted / blocked;
- N, WR, PF, expectancy, net, max loss streak;
- accepted trades per week;
- contribution by source clock;
- exact-timestamp tie count.

## BTC-quality gate
Frozen BTC B27DX LONG benchmark:
- WR **71.9%**;
- PF **2.22**;
- expectancy **+$1.26/trade**;
- max loss streak **3**.

`BTC_QUALITY_SUPPORTED` requires the 0-bps Pooled Major ETH portfolio to meet or exceed:
- WR >= 71.9%;
- PF >= 2.22;
- expectancy >= +$1.26/trade;

and every major partition must have positive net and PF > 1.0.

The user's ~2 opportunities/week objective is reported as a frequency diagnostic, not used to override quality.

## Stress gate
At 5 bps execution stress, Pooled Major must retain:
- PF >= 1.0;
- net >= 0.

## Decision states
- `ETH_S4_PORTFOLIO_BTC_QUALITY_SUPPORTED`
- `ETH_S4_PORTFOLIO_POSITIVE_BELOW_BTC_QUALITY`
- `ETH_S4_PORTFOLIO_NOT_SUPPORTED`
- `ETH_S4_PARITY_FAILED`

## Guardrails
- No parameter tuning in S4.
- No clock pruning based on performance.
- No runner or leverage changes.
- No H/H2 selection.
- No live BBC changes.
