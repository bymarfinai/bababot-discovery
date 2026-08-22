# B27S — London -> New York LONG Entry Staleness / TTL Optimization — Preregistration

## Purpose
Test whether B27R K1 entries fail because limit orders remain active too long after the audited B27Q liquidity-pressure signal.

This experiment changes ONLY how long a retrace order remains eligible. It does not change the B27Q detector, direction, session, touch count, stop, target, or fees.

## Frozen primary cohort
Inherited unchanged from B27R:
- transition `LONDON_TO_NEWYORK`;
- LONG after first distinct visit to completed London High (`K1`);
- `OPP0`: zero London-Low visits known at signal time.

Secondary diagnostic cohort: exact same setup at `K2`. It cannot replace K1 based on B27S results.

## Frozen entry prices
Use only preregistered B27R range fractions, no new price interpolation:
- F50 = L + 0.50*(H-L)
- F60 = L + 0.60*(H-L)
- F65 = L + 0.65*(H-L)
- F70 = L + 0.70*(H-L)
- F75 = L + 0.75*(H-L)
- F80 = L + 0.80*(H-L)

F55 is intentionally omitted to keep the staleness grid smaller; no new fraction is added after B27R results.

## Frozen order time-to-live (TTL)
Each limit becomes eligible on the first 5m bar starting at `signal_ts`, exactly as B27R.

Predeclared TTL variants:
- T15 = 15 minutes
- T30 = 30 minutes
- T45 = 45 minutes
- T60 = 60 minutes
- T90 = 90 minutes
- FULL = until active-session end (B27R-equivalent control)

A fill is allowed only on an eligible 5m bar whose START time is strictly before `signal_ts + TTL`. Once that boundary is reached, an unfilled order is cancelled `TTL_EXPIRED`.

Before fill, any strict 5m close above H or below L still cancels the order `RANGE_BROKE_BEFORE_FILL` before considering a same-bar limit fill.

## Exit / economics
Unchanged from B27R:
- LONG TP = frozen London High H;
- LONG SL = frozen London Low L;
- conservative fill-bar handling: stop touch on fill bar = SL; target-only on fill bar is not awarded;
- from the next 5m bar first barrier resolves; same-bar TP+SL = conservative SL;
- unresolved positions time-exit at New York session end;
- notional $500;
- round-trip fee $0.40.

## Primary development selection
Selection can access ONLY external + development K1/OPP0 rows.

A `(fraction, TTL)` pair is DEV_ELIGIBLE only if BOTH external and development have:
- >= 20 filled/resolved trades;
- positive fee-sensitive net expectancy;
- net PF >= 1.10.

If multiple pairs qualify, select exactly one by:
1. highest minimum PF across external/development;
2. highest pooled external+development net expectancy;
3. highest minimum fill count.

If none qualify, no candidate is selected.

## Reference-validation check
Only after selection, read the selected exact pair on reference_validation.

REFERENCE_PASS requires:
- >= 15 fills;
- positive net expectancy;
- PF >= 1.20.

This remains historical reference validation, not pristine independent OOS.
August is telemetry only.

## Mandatory assertions
Abort before persistence if any fail:
1. every source signal identity comes unchanged from B27Q;
2. all primary/secondary signals are London->NY LONG, OPP0, K1/K2 only;
3. planned fraction price exactly matches the frozen formula;
4. no fill occurs before signal_ts;
5. no TTL-limited fill starts at or after its expiry boundary;
6. FULL exactly reproduces B27R fraction-method fills and economics for the same signal/fraction;
7. no filled order has a strict range close-break before fill;
8. TP/SL remain H/L;
9. selection cannot access reference_validation/August before choosing the candidate.

Research only. Live BBC unchanged.
