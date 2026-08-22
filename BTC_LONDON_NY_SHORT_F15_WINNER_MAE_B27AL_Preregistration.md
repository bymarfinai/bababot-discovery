# B27AL — BTC London->NY SHORT F15 Winner MAE / Stop-Distance Audit — Preregistration

## Purpose
Freeze the independently discovered B27AK F15 SHORT retrace zone and answer the same narrow path question previously asked for LONG F85 in B27X:

**After K1 Low pressure, a causal leave from Touch #1, and a valid F15 SHORT fill strictly before H2, how far do trades that eventually reach H2 move adversely ABOVE the F15 entry?**

This is diagnostic only. It does not select a stop, confirmation trigger, target, runner, or live rule.

## Frozen upstream logic
- BTCUSDT raw repository 5m clock and frozen partitions.
- `LONDON_TO_NEWYORK`, SHORT, B27Q K1, OPP0.
- H/L are completed London-session High/Low.
- B27AD/B27AK low-touch episode, causal leave, and terminal chronology unchanged.
- F15 = `L + 0.15*(H-L)`; B27AK independently established F15 as the only passing SHORT retrace zone.
- Fill must occur after causal leave and strictly before H2/opposite terminal bar.
- H2 = first later raw 5m bar with `low <= L`, including a breakdown-on-arrival bar.
- No 4H regime gate.

B27AL must reproduce B27AK F15 identities exactly before path diagnostics are interpreted: external 50 fills / 37 H2; development 79 / 59; reference_validation 34 / 24; august 1 / 1.

## Winner definition
`F15_H2_WINNER` = frozen B27AK F15 fill whose terminal window outcome is H2 arrival.

## Adverse excursion
Range fraction is London Low=0, High=1; F15 entry fraction=0.15. For SHORT, adverse movement is UPWARD.

For H2 winners persist:
1. maximum 5m high from fill bar through last bar strictly before H2;
2. conservative maximum high from fill bar THROUGH the H2 bar;
3. contextual maximum excluding the fill bar.

Required adverse distance D = `max(0, maximum_fraction - 0.15)`.

Report N, P50, P75, P90, P95, max by partition for pre-H2 and conservative-through-H2.

## Diagnostic stop-survival curve
Freeze D05, D10, ..., D85. Stop fraction = `0.15 + D`.
A winner survives only when maximum high is strictly BELOW stop fraction. Equality counts as stop touched.

No distance is selected or promoted.

## Failure comparison
For filled F15 candidates that do not reach H2, measure maximum high through terminal bar (inclusive for opposite/ambiguous terminal) or active-session end, and report required-distance quantiles.

## Mandatory assertions
1. full 5m coverage reproduces;
2. B27AK F15 fill/H2 identities reproduce exactly;
3. entry fraction/price is exact F15;
4. every winner has H2 strictly after fill;
5. pre-H2 interval excludes H2 bar; conservative interval includes it;
6. fill-bar high is included conservatively;
7. stop survival uses strict `< stop`; equality = stopped;
8. all path timestamps/highs come from raw 5m;
9. no economics or regime information affects this audit;
10. synthetic mirror tests pass before persistence.

Research only. Live BBC unchanged.
