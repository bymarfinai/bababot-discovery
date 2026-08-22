# B27AG — BTC London -> New York 4H HH/HL Regime Alignment Audit — Preregistration

**Status:** PREREGISTERED. Attribution audit only. No threshold, entry, stop, target, runner, timeframe, or session parameter may be changed after seeing results.

## Question
Is the LONG/SHORT asymmetry in the frozen B27Q -> F85/F15 pipeline explained by trading the local liquidity direction against the already-known broader 4H market-structure regime?

## Frozen local setup
- BTCUSDT perpetual, London -> New York only.
- B27Q K1 OPP0 signals are reused unchanged.
- LONG structural cohort: B27W F85.
- SHORT structural cohort: B27AD BLIND_F15.
- LONG confirmed-entry economics: existing B27AC EARLY_RECLAIM.
- SHORT confirmed-entry economics: existing B27AD EARLY_REJECT.
- H2 remains a milestone, not TP.
- E20 levels remain exactly H + 0.20R for LONG and L - 0.20R for SHORT.
- Existing fixed-E20 and hybrid E20-lock economics are reused; no re-optimization.

## Frozen 4H regime detector
Use the repository's pre-existing `v4h_regime_endpoint.py` `SwingRegime` semantics with its existing defaults, reproduced exactly:
- 4H UTC bars.
- EMA fast = 7; EMA slow = 20.
- swing lookback `slb = 5`.
- swing ATR separation `sa = 0.5`.
- ATR period = 14 using the existing implementation.
- A swing candidate is centered at `i - slb//2` and only becomes known when bar `i` is complete.
- Higher/lower swing counters follow the existing implementation.
- BULL only when `hh >= 2`, `hl >= 2`, EMA7 > EMA20, and completed 4H close > EMA20.
- BEAR only when `lh >= 2`, `ll >= 2`, EMA7 < EMA20, and completed 4H close < EMA20.
- Otherwise SIDEWAYS.

No alternative regime mode (`ema_simple`, `ema_cross`, `dual`) is tested in B27AG.

## Causal availability
The state attached to a B27Q signal is the state of the latest **completed** 4H UTC candle whose availability time (`bar_start + 4h`) is <= the B27Q K1 `signal_ts`.

The incomplete 4H candle containing the signal may not contribute any OHLC, EMA, ATR, swing, or state information.

For executed entries, also record the latest completed 4H state available at the entry timestamp and whether it changed after signal; this is diagnostic only. Primary attribution uses state at K1 signal completion.

## Alignment labels
At K1 signal time:
- LONG + BULL = `ALIGNED`.
- SHORT + BEAR = `ALIGNED`.
- LONG + BEAR = `COUNTER`.
- SHORT + BULL = `COUNTER`.
- Either direction + SIDEWAYS = `SIDEWAYS`.

No observations are dropped because of regime.

## Frozen outcomes
For each side x regime x partition and pooled major report:
1. K1 opportunity count and state distribution.
2. B27Q same-side `TARGET_BREAK` rate.
3. causal clean-window rate.
4. F85/F15 fill rate conditional on clean window.
5. H2 rate conditional on fill.
6. post-H2 strict same-side breakout acceptance rate.
7. E20 reach rate conditional on H2.

For existing executed economics, report by signal-time regime:
- blind exact-mirror fixed E20 and hybrid E20-lock PnL where available;
- primary confirmed-entry fixed/hybrid economics: LONG EARLY_RECLAIM vs SHORT EARLY_REJECT;
- N, WR, PF, expectancy/trade, and total net.

## Hypothesis readout
The user's regime hypothesis is directionally supported only if the observed ordering is consistent with all of the following in pooled major data:
1. SHORT+BEAR H2 rate > SHORT+BULL H2 rate.
2. SHORT+BEAR E20/H2 rate > SHORT+BULL E20/H2 rate.
3. LONG+BULL H2 rate > LONG+BEAR H2 rate.
4. LONG+BULL E20/H2 rate > LONG+BEAR E20/H2 rate.
5. Existing confirmed-entry fixed-E20 expectancy for aligned trades is greater than counter-regime expectancy.

This is an attribution readout, not a promotion gate. Small regime cells must be shown explicitly and may make the conclusion inconclusive.

## Mandatory audits
- Raw 5m coverage remains 100%.
- Resampled 4H bars use only complete 5m constituents and UTC 4-hour boundaries.
- Regime implementation must match the existing `SwingRegime` formulas and defaults exactly.
- State availability timestamp must never exceed signal/entry timestamp.
- B27Q opportunity identities, B27W F85 fills, and B27AD F15 fills must reproduce persisted cohorts.
- No H2/acceptance/E20 scan may start from future data.
- No result-dependent threshold or alternative regime detector is allowed.

Research only. Live BBC unchanged.
