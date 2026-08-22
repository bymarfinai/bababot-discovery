# B27U — London -> New York Shallow Entry + Local Range Stop — Preregistration

## Purpose
Optimize trade geometry after B27T showed that successful K1 High-pressure paths typically remain in the upper part of the previous-session range, while B27R used the distant previous-session Low as stop and therefore produced poor reward:risk.

B27Q signal identity remains frozen. This experiment changes only entry/stop geometry.

## Cohorts
Primary: LONDON_TO_NEWYORK, LONG, K1 High-pressure, OPP0.
Secondary diagnostic: same at K2 OPP0.
Partitions remain external, development, reference_validation, August.

## Frozen entry levels
Range fraction f is Low=0, High=1.
- F75 entry = 0.75
- F80 entry = 0.80
- F85 entry = 0.85

Limit becomes eligible from the first 5m bar after signal completion, exactly as B27Q/B27R. Any strict 5m close outside previous-session H/L before fill cancels the order.

## Frozen local stops
For each filled entry, test only two stop distances measured in previous-session range units:
- D10: stop = entry fraction - 0.10
- D15: stop = entry fraction - 0.15

Thus predeclared pairs are:
- F75/D10 -> stop F65, nominal target-to-stop RR 2.5
- F75/D15 -> stop F60, nominal RR 1.67
- F80/D10 -> stop F70, nominal RR 2.0
- F80/D15 -> stop F65, nominal RR 1.33
- F85/D10 -> stop F75, nominal RR 1.5
- F85/D15 -> stop F70, nominal RR 1.0

Target remains frozen previous-session High. No breakout-extension target is introduced in this experiment.

## Resolution
- On fill 5m bar, if local stop is touched, score conservative SL; target-only touch on fill bar is not awarded.
- From next bar onward, first wick touch of target or local stop resolves; same-5m both -> conservative stop.
- If unresolved at New York session end, time-exit at first available 5m open at/after session end.
- Illustrative notional $500; round-trip fee $0.40.

## Evaluation
Report setup count, fill rate, W/L, WR, TP rate, PF, expectancy, total net, median nominal RR by partition / K / entry / stop.

A primary K1 candidate is only marked SCREEN_PASS when the exact pair has >=30 resolved fills, positive expectancy, and PF >=1.20 in each of external, development, and reference_validation. This is discovery evidence only, not independent OOS promotion.

## Mandatory assertions
- B27Q signal identity unchanged.
- Exact fraction entry and stop geometry.
- No same-signal-bar fill.
- No fill after strict H/L close-break.
- Local stop < entry < target for every trade.
- Same-bar ambiguity conservative.

Research only; live BBC unchanged.