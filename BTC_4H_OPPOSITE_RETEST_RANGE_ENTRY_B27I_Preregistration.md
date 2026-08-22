# B27I Preregistration — BTC 4H Opposite-Side Retest Entry Before Range Breakout

Research only. Do not modify live BBC.

## Hypothesis

A repeated attack on one side of a frozen 4H swing range may create directional pressure. Instead of buying near resistance or shorting near support, enter from the opposite side of the range on a later retest.

Bull example: High zone has already been visited at least twice; when price later makes a qualifying second-or-later Low-zone retest, enter LONG from the Low side and test whether the High subsequently breaks.

Bear example is symmetric.

## Data and partitions

Use the same Binance BTCUSDT 5m source and frozen B22B partitions used by B27A–B27H. Resample causally to 4H. No future data may be used to identify a swing.

## Causal swing range

A 3-bar fractal pivot centered at bar k is known only after k+1 has completed.

After a reset, collect the first causally-confirmed swing high and first causally-confirmed swing low. Once both exist and high > low, freeze them as one active range. Minor later pivots do not replace the frozen boundaries. The range remains active until a 4H candle closes strictly above the frozen High or strictly below the frozen Low.

After either close-through breakout, discard the range and wait for a new pair of confirmed pivots formed after the reset.

## Retest zones

Tolerance is fixed at 0.20% of each frozen boundary.

High-zone visit: candle high >= High * (1 - 0.002) AND candle close <= High.
Low-zone visit: candle low <= Low * (1 + 0.002) AND candle close >= Low.

Consecutive qualifying candles in the same zone count as one visit. The price must leave that zone before a later visit can increment the count again.

If one 4H candle qualifies for both High and Low zones, treat the candle as path-ambiguous and count neither zone visit for signal purposes.

## Entry logic

Only one entry is allowed per frozen range.

### LONG
On a newly-started Low-zone visit, enter LONG at the next 4H open only if:
- High-zone distinct visits already >= 2, and
- this Low-zone visit makes Low-zone distinct visits >= 2, and
- the current 4H candle closes inside the frozen range (no breakout).

### SHORT
Symmetric. On a newly-started High-zone visit, enter SHORT at the next 4H open only if:
- Low-zone distinct visits already >= 2, and
- this High-zone visit makes High-zone distinct visits >= 2, and
- current candle closes inside the range.

If both LONG and SHORT would somehow qualify on the same 4H candle, skip the candle as ambiguous.

Record the number of target-side pressure visits already present at entry: 2 exactly or 3+.

## Stop and target

LONG stop = Low of the signal/retest 4H candle.
SHORT stop = High of the signal/retest 4H candle.
Entry = next 4H open.
TP = 2R from entry.

Resolve TP/SL using underlying 5m bars. If TP and SL are both hit in the same 5m bar, count SL conservatively. Fee assumption remains $0.40 round trip on $500 notional.

One trade at a time. A range is consumed after its first entry and cannot generate another trade even if the trade exits before the range itself breaks.

## Structural diagnostic

For each entry, also record whether a 4H close-through breakout of the intended target boundary occurs before the 5m stop is first hit:
- LONG target boundary = frozen High.
- SHORT target boundary = frozen Low.

This diagnostic is not a separate entry rule.

## Reporting

For external, development, reference_validation, and august report:
- N, LONG/SHORT, W/L, WR, net PF, net expectancy/trade, total net, median stop, median hold;
- intended-boundary breakout-before-stop rate;
- results by target-side pressure visits at entry: exactly 2 vs 3+;
- LONG and SHORT diagnostics.

## Gate

Primary setup PASS only if external, development, and reference_validation each have:
- >= 30 resolved trades,
- positive fee-sensitive expectancy/trade,
- net PF >= 1.20.

Subgroup diagnostics are not promoted post hoc. Any subgroup that looks good requires a new preregistered experiment.
