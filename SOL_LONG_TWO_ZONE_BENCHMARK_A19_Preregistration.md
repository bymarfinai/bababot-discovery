# SOL LONG Two-Zone Operational Benchmark — A19 Preregistration

## Purpose
A17 supported a second SOL parent habitat at `R420 / 03:00 UTC`. A18 rejected copying `REC_H2` into that zone.

The only supported two-zone architecture is therefore frozen as:

- **Mature zone:** `R240 / 18:00 UTC / A2 E0_RESTING_H -> E40 + A4 REC_H2`;
- **Expansion zone:** `R420 / 03:00 UTC / A17 E0_RESTING_H -> E40`, **parent only**.

A19 performs no strategy search. It benchmarks whether this already-supported architecture materially improves the SOL system as a portfolio of trade components.

## Frozen rules
- All 18:00 parent and H2 rules remain exactly A2/A4.
- All 03:00 parent rules remain exactly A17.
- No 03:00 H2 recovery; A18 rejected it.
- No H3/H4.
- No A6/A8/A10/A11/A12/A14/A16 mechanisms.
- Same $500 notional per component trade.
- Same 5bps per-trade stress semantics already used by each component.
- No clock, reference, entry, target, lifecycle, or cost retuning.

## Benchmark partitions
Report separately for:
- Development;
- External;
- Reference Validation.

For each partition compare:
1. mature 18:00 stack alone;
2. new 03:00 parent alone;
3. additive two-zone stack.

## Required economics
For mature and combined stacks report:
- component-trade N;
- trades/week;
- WR;
- PF;
- expectancy/component trade;
- net;
- 5bps WR/PF/expectancy/net;
- realized-exit equity max drawdown raw and 5bps;
- annualized net raw and 5bps;
- total realized exposure-hours;
- net per exposure-hour raw and 5bps.

For the expansion zone report its incremental N/net and stress net.

## Capital/concurrency diagnostics
Using actual frozen entry/exit timestamps:
- fraction of 03:00 parent trades whose open interval overlaps any mature A2/A4 component;
- peak concurrent component positions in the additive stack.

Overlap is diagnostic only. A19 does not invent a single-position scheduler or use future overlap information to alter trades.

## Benchmark interpretation gate
The two-zone architecture is called **supported additive expansion** only if, in all three partitions:
- combined raw net > mature raw net;
- combined 5bps net > mature 5bps net;
- combined raw PF > 1.00;
- combined 5bps PF > 1.00;
- the 03:00 incremental parent net is positive raw and after 5bps.

No requirement is imposed that combined PF must exceed mature PF; a positive independent zone may rationally trade some PF for materially higher total net/frequency. The exact PF change must be reported.

A19 does not authorize live deployment. If concurrency is operationally meaningful, a later capital-allocation/scheduler experiment must be causal and preregistered.

Research only. Live Baba Bot remains unchanged.
