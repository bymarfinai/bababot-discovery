# ETH London -> New York M9A Audit Fix

M9 result-bearing execution completed with the intended frozen trade semantics, but its audit flag incorrectly reported M8 baseline parity `FAIL` because the August partition has zero trades and therefore `NaN` WR/PF fields. The original checker used ordinary numeric subtraction, under which `NaN` vs `NaN` evaluates false.

M9A changes **no trade, floor, target, stop, fee, slippage, chronology, metric, partition, or promotion rule**. It only validates the already-persisted M9 outputs with:

1. NaN-safe equality for zero-N partition metrics;
2. exact baseline E15/F50 parity against M8 for N, WR, PF, net, 5bps PF, and 5bps net;
3. explicit assertion that every post-breakout floor/ambiguous event occurs no earlier than the first bar after breakout confirmation;
4. persisted row-count and cohort identity sanity checks.

No M9 economic number may be changed by M9A. If validation passes, the existing M9 result is considered audit-valid; if it fails, M9 remains invalid.