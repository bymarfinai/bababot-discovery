# B27J Preregistration — BTC 4H Second Opposite-Side Retest Entry

Research only. Live BBC unchanged.

This is an additive correction to B27I. B27I required two target-side visits before the second opposite-side retest and produced almost no samples. B27J implements the causal sequence actually intended in the prior discussion.

## Frozen range
Use the same causal 4H 3-bar swing range construction as B27I. After reset, first confirmed swing high + first confirmed swing low are frozen as one range until a strict 4H close outside either boundary. Minor pivots do not replace the range.

## Zones
Tolerance = ±0.20% of each frozen boundary.
High visit: high >= High*(1-0.002), close <= High.
Low visit: low <= Low*(1+0.002), close >= Low.
Consecutive qualifying candles in one zone count as one distinct visit. A candle touching both zones is path-ambiguous and counts neither.

## Entry
Only one trade per frozen range.

LONG sequence requirement at the signal candle:
- current candle starts the second-or-later distinct Low-zone retest;
- at least one distinct High-zone visit has already occurred;
- candle closes inside the frozen range;
- enter LONG at next 4H open.

SHORT symmetric:
- current candle starts the second-or-later distinct High-zone retest;
- at least one distinct Low-zone visit has already occurred;
- enter SHORT next 4H open.

If both directions qualify on one candle, skip as ambiguous.

Record target-side visits already known at entry (1 exactly vs 2+), but do not use future visits to decide entry.

## Risk / exit
LONG SL = signal/retest candle Low. SHORT SL = signal/retest candle High. TP = 2R. Resolve on 5m; same-5m TP+SL = SL. Fee = $0.40 round trip on $500 notional.

## Diagnostics
Also record causally subsequent outcomes:
1. target boundary WICK reached before the 5m stop;
2. target boundary strict 4H CLOSE breakout before the 5m stop.

LONG target boundary = frozen High; SHORT target = frozen Low.

## Reporting and gate
Report external/development/reference_validation/august with N, WR, PF, expectancy, PnL, target-touch-before-SL rate, target-close-breakout-before-SL rate, and side / target-visits-at-entry diagnostics.

Primary PASS requires all three major partitions to have >=30 resolved trades, positive net expectancy, and PF >=1.20.
