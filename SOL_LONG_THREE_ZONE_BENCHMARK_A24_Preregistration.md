# SOL LONG Three-Zone Portfolio Benchmark — A24 Preregistration

## Purpose
Audit the additive portfolio economics of all currently supported SOL LONG habitats without changing any trade.

## Frozen architecture
- `03:00 UTC / R420`: A17 parent-only `E0_RESTING_H -> E40`; A18 recovery rejected.
- `15:00 UTC / R360`: A20 parent-only `E0_RESTING_H -> E40`; A23 recovery rejected.
- `18:00 UTC / R240`: A2 parent + A4 `REC_H2`.
- Target remains E40.
- Same Development / External / Reference Validation partitions.
- Same notional and 5bps stress convention.

## Comparisons
For each partition report:
1. 18UTC mature stack alone.
2. 03UTC parent alone.
3. 15UTC parent alone.
4. Existing two-zone stack: 18 + 03.
5. Three-zone stack: 18 + 03 + 15.

## Metrics
- trades/week
- WR
- PF
- expectancy
- net
- 5bps PF / expectancy / net
- max drawdown raw / 5bps
- annualized net
- exposure hours
- net per exposure-hour
- 15UTC overlap with the existing two-zone stack
- peak concurrent components

## Additive support gate
A24 is supported only if, in Development, External, and Reference Validation:
- 15UTC parent net > 0 raw and 5bps
- three-zone net > two-zone net raw and 5bps
- three-zone PF > 1.0 raw and 5bps

No trades are suppressed because of overlap. Overlap is diagnostic only and cannot use future information.

Research only. Live Baba Bot remains unchanged.
