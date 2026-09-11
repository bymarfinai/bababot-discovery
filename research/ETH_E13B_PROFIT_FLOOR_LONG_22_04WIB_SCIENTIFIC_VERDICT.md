# ETH E13B — Sequential LONG Minimum-Profit-Floor Scientific Verdict

## Status
**ETH_E13B_NO_PROFIT_FLOOR_PASSER**

Development/shadow only. OOS remained closed.

## Result-bearing run
- workflow run: **34577950291**
- job: **103194639307**
- head SHA: **b7f9269db8008b831fd3652983c74b24f2f875b3**
- artifact: **10190402243**
- artifact SHA256: **03b0890e936b3f767f634513d1434412de2c3871a8d4e20819ddb006455d33f6**
- raw ETHUSDT 5m coverage: **100.0000%**

## Formal result
**0 / 49 candidates passed the frozen pooled + cross-era gates.**

E13B retained one-position causal execution and used only E12 formal LONG characters. It crossed seven completed-close net-profit floors (0.10% to 1.50% of $500 notional) with seven max holds (4h to 48h).

## Main result
Unlike E13A, raising the required profit floor successfully restored positive economics in many cells. Therefore the E13A failure was specifically caused by harvesting profits that were too small, not by the one-position concept alone.

Examples:
- net floor 0.30% / 48h: N549, WR 91.62%, net **+$174.97**, exp **+$0.32**, PF1.166, DD$159.92.
- net floor 0.50% / 48h: N488, WR 87.50%, net **+$268.11**, exp **+$0.55**, PF1.221, DD$202.80.
- net floor 0.75% / 36h: N461, WR79.39%, net **+$301.01**, exp **+$0.65**, PF1.202, DD$166.44.
- net floor 1.00% / 36h: N447, WR **75.17%**, net **+$473.34**, exp **+$1.06**, PF **1.2949**, DD **$143.66**, max loss streak 5, timeout 26.62%.
- net floor 1.50% / 36h: N404, WR69.06%, net **+$557.93**, exp **+$1.38**, PF1.320, DD$170.51.

## Closest balanced near-miss — descriptive only
**Net floor 1.00% ($5.00) / max hold 2160m (36h)** is the cleanest balanced E13B near-miss.

Pooled:
- N **447**
- WR **75.17%**
- net **+$473.34**
- expectancy **+$1.0589/trade**
- PF **1.2949**
- DD **$143.66**
- max loss streak **5**
- timeout **26.62%**
- median duration **520m**
- p90 duration **2160m**

It narrowly misses the pooled PF >=1.30 gate and DD <=$125 gate.

Era:
- 2022: N141, WR **80.85%**, net +$53.57, exp +$0.38, PF **1.078** -> fails the frozen PF>=1.15 era floor.
- 2023: N147, WR **66.67%**, net +$115.09, exp +$0.78, PF1.248 -> passes E13B yearly floors.
- 2024: N159, WR **77.99%**, net +$304.68, exp +$1.92, PF1.665 -> passes strongly.

Thus the remaining problem is not absence of positive payoff. It is residual path risk and weaker 2022 payoff efficiency when all four E12 formal source hours are allowed into the sequential executor.

## Scientific interpretation
E13A established that "first green close" is too shallow. E13B establishes that a meaningful profit floor can turn the same sequential framework economically positive. The next unresolved question is **source selection**: do all four E12 formal hour-characters belong in the same live sequential executor, or does one or more source hour create the remaining drawdown / low-PF behavior?

## Next scientific action
Freeze the E13B closest balanced coordinate exactly at **net floor 1.00% / max hold 36h** and run a new preregistered source-subset experiment across all non-empty subsets of the four E12 formal source hours. Do not tune target or hold inside that source-subset experiment. Keep E13B gates unchanged.

No OOS exposure. No live promotion.