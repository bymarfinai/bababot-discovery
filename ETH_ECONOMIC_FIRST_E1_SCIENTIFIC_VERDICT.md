# ETH Economic-First Reset — E1 Scientific Verdict

**Verdict: NO DEVELOPMENT CANDIDATE.**

Official status: `ETH_ECONOMIC_FIRST_E1_NO_DEV_CANDIDATE`.

E1 deliberately removed H/L/range/breakout/retest logic and tested whether ETH had a raw weekday time-of-day directional drift that was already economically healthy under a minimal executable rule.

## Search
- ETHUSDT Binance Futures raw 5m, 100% coverage.
- Development only for selection: 2022-01-01 to 2025-01-01 UTC.
- Weekday anchors.
- 48 half-hour UTC entry clocks.
- LONG and SHORT.
- fixed holds 15/30/60/90/120/180/240/360/480/720/960m.
- exact 5m open entry and exact 5m open exit.
- $500 fixed notional.
- $0.75 round-trip fee.
- 1,056 Development candidates.

## Result
- Healthy economic gate passers: **0 / 1,056**.
- Full healthy + local-stability passers: **0 / 1,056**.
- Holdouts were not opened.

Best raw Development net economics, descriptive only:

**18:30 UTC (01:30 WIB) / LONG / hold 720m**
- trades: **781**;
- WR: **49.17%**;
- net PnL: **+$80.88**;
- expectancy: **+$0.10/trade**;
- PF: **1.027**;
- max DD: **$257.39**;
- max loss streak: **6**;
- positive chronological blocks: **2/4**;
- supportive local neighbors: **0/4**.

The highest-WR Development coordinate was:

**12:30 UTC (19:30 WIB) / SHORT / hold 240m**
- WR: **52.43%**;
- net PnL: **-$153.74**;
- expectancy: **-$0.20/trade**;
- PF: **0.945**;
- max DD: **$314.36**.

Thus neither raw PnL nor raw WR exposes a sufficiently healthy pure-clock character. The best positive-net coordinate is weak, unstable, and drawdown-heavy; the highest-WR coordinate loses money after cost.

## Scientific conclusion
Pure weekday **clock → fixed direction → fixed hold** drift is closed as the primary ETH character family. It should not be rescued by relaxing E1 gates, adding H filters, or tuning the same coordinate more densely.

The next economic-first family should add exactly one causal conditioning variable while preserving direct economic selection. The strongest next family is **pre-entry drive sign → momentum versus reversal**, because it tests whether ETH's character depends on what price did immediately before the clock rather than on an H boundary.

That family should use:
- a bounded lookback-duration grid;
- a bounded forward-hold grid;
- momentum and reversal as exact mirror modes;
- all actual economics and WR after fee as selection objectives;
- Development-only selection, local stability, and unopened holdouts until one candidate is frozen.

If that family also fails, close it and move again rather than returning to H continuation optimization.

Research/shadow only. No live promotion or profit guarantee.
