# B27O — BTC 15m First Previous-Session Retest -> Midpoint Entry

## Hypothesis
A first causal retest of the completed previous-session High/Low may identify directional pressure early enough to enter on a retrace to the midpoint of that same completed previous-session range.

## Frozen setup
- Research only; live BBC unchanged.
- Source and frozen partitions: same as B27M/B27N.
- Previous-session windows and transitions are unchanged from B26C/B27M:
  - Asia 00:00-08:00 UTC -> London 08:00-13:30 UTC.
  - London 08:00-13:30 UTC -> New York 13:30-20:00 UTC.
- Weekdays only.
- Decision timeframe: 15m, anchored to active-session start.
- Previous-session High and Low are frozen only after previous session completes.
- Retest zone tolerance: +/-0.20% around the frozen level.
- A retest is a 15m bar intersecting the zone without a strict close beyond the frozen boundary.
- Consecutive zone-intersecting bars are one visit. This experiment acts only on the first distinct visit.

## Direction and signal
- If the first unambiguous level visit is the previous-session High: BULL setup.
- If the first unambiguous level visit is the previous-session Low: BEAR setup.
- If the same 15m bar intersects both High and Low zones before a directional first visit can be ordered, skip the day as intrabar-ambiguous.
- If a strict 15m close breaks either boundary before any valid first retest, no setup.
- Signal becomes causally known only at the end of the first-retouch 15m bar.

## Entry
- Midpoint = (previous-session High + previous-session Low) / 2.
- After a BULL first-High-retest signal, place a BUY limit at midpoint starting from signal-bar end.
- After a BEAR first-Low-retest signal, place a SELL limit at midpoint starting from signal-bar end.
- Use underlying 5m bars to detect the first midpoint fill.
- Entry price is exactly the frozen midpoint.
- If midpoint is never reached before active-session end, record NO_FILL and no trade.

## Exit
- BULL: SL = previous-session Low; TP = previous-session High.
- BEAR: SL = previous-session High; TP = previous-session Low.
- Midpoint makes nominal reward:risk exactly 1:1 before fees.
- Resolve barriers on underlying 5m bars after fill.
- If TP and SL are both touched in the same 5m bar, count conservative SL.
- If unresolved by active-session end, exit at first 5m open at/after session end.
- Illustrative notional: $500.
- Fee: $0.40 round trip.

## Outputs
For each partition and transition report: setups, fills, fill rate, wins/losses, fee-sensitive WR, PF, expectancy/trade, total net PnL, TP rate, time-exit rate, and side split.

## Repeatability gate
A transition passes only if external, development, and reference_validation each have >=100 filled trades, positive net expectancy, and net PF >=1.20. August is diagnostic only.
