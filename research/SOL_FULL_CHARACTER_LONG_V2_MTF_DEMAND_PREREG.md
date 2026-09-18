# SOL Full-Character Long V2 — MTF Demand Preregistration

## Objective
Test a materially different full LONG character suggested by the supplied educational example: an H1 bullish impulse/new-high/demand-pullback setup nested inside a still-fresh H4 bullish demand context.

**H4 bullish impulse -> H4 new high -> fresh H4 demand**
then
**H1 bullish impulse -> H1 new high -> H1 demand pullback overlapping H4 demand**
then
**5m sweep H1 demand-low -> reclaim -> LONG**.

This is a new full-character hypothesis, not a rescue or retune of Full-Character Long V1.

## Frozen data and evaluation
- SOLUSDT from the existing 5m dataset.
- Parent context timeframe: H4.
- Setup timeframe: H1.
- Entry trigger timeframe: 5m.
- Evaluation: 2020-2024.
- 2025+ remains CLOSED.
- Long only.
- Entry: next 5m open after trigger.
- Fixed +60m diagnostic exit.
- Round-trip cost 0.15%.
- $500 notional.
- No hours, EMA, RSI, Fibonacci, volume, regime, TP/SL optimization, or post-result rescue.

## Frozen H1 setup
Reuse `detect_full_character()` from `sol_full_character_long_v1.py` exactly, unchanged.
Therefore the H1 character remains:
- causal H1 2-left/2-right swings,
- bullish impulse that closes above prior H1 swing high / creates new high,
- impulse leg 1-12 H1 bars,
- displacement >= 1.5 x median prior-20 H1 range,
- close-path efficiency >= 0.60,
- H1 demand = last bearish H1 candle inside the impulse leg, zone low -> open,
- first fresh H1 retracement back to that demand within 24H, without H1 close below demand low.

## Frozen H4 parent-demand construction
Build causal H4 bars from the same 5m dataset and apply the same structural logic at H4:
- 2-left/2-right causal H4 pivots,
- prior H4 swing high H0 followed by H4 swing low L1,
- first later completed H4 close strictly above H0,
- impulse leg 1-12 completed H4 bars,
- displacement >= 1.5 x median H4 high-low range over the 20 completed H4 bars before L1,
- close-path efficiency >= 0.60,
- H4 demand = last bearish H4 candle from L1 through the bar immediately before the H4 breakout, zone low -> open.

Parent H4 demand activates only after the H4 breakout bar closes.

## Frozen nested-demand eligibility
For each already-frozen H1 full-character event:
1. Consider the H1 return bar that completed the H1 demand-pullback structure.
2. Search backward for the most recent H4 demand zone whose activation was already known before that H1 return bar began.
3. The H4 zone must still be fresh immediately before the H1 return bar:
   - from H4 activation through the final completed 5m bar before the H1 return bar begins, no completed 5m low may have touched or crossed H4 demand-top;
   - no completed 5m close may have closed below H4 demand-low.
4. The H1 return bar itself must touch the H4 demand zone: H1 return-bar low <= H4 demand-top and H1 return-bar close >= H4 demand-low.
5. H1 demand and H4 demand must overlap as price intervals. Any non-empty overlap qualifies; no overlap-percentage threshold is used.
6. Use only the most recent qualifying fresh H4 demand zone.

If no qualifying H4 parent demand exists, that H1 event is not part of V2.

## Frozen 5m entry trigger
Use only the exact V1 trigger `DEMAND_SWEEP_RECLAIM` on the H1 demand zone.
After H1 structure-ready time, observe at most 24 completed 5m bars / 120 minutes.
Before entry, any completed 5m close strictly below H1 demand-low invalidates the opportunity.
Trigger on the first completed 5m bar with:
- low < H1 demand-low, and
- close > H1 demand-low.
Entry is the next 5m open.

## Outputs
Report:
- total V1 H1 full-character events,
- number retaining a qualifying fresh H4 parent demand,
- nested-character incidence by year,
- H4 impulse diagnostics and H1/H4 zone overlap diagnostics,
- triggered N and conversion rate,
- WR +60m, net expectancy, PF, PnL, max DD, max loss streak,
- clean-up-impulse incidence, median MFE/MAE, trigger delay,
- yearly 2020/21/22/23/24 economics.

## Frozen promotion gates
Keep the exact V1 gates:
1. Triggered N >= 100.
2. Pooled +60m net expectancy > 0.
3. Pooled PF >= 1.15.
4. Positive PnL in >= 4 of 5 years.
5. Median MFE/|MAE| >= 1.20.

`PASS_TO_CHARACTERIZATION` requires all five.
`REJECTED_AS_DEFINED` means this exact nested H4->H1 character plus exact sweep/reclaim entry is not promoted.
No rescue on 2020-2024 by changing H4/H1 pivot order, impulse thresholds, freshness semantics, overlap semantics, trigger window, hours, indicators, regime filters, TP or SL.