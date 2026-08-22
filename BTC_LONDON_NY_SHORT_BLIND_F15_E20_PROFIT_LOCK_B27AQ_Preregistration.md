# B27AQ — BTC London->NY SHORT BLIND_F15 E20 Profit-Lock Audit — Preregistration

## Purpose
Test the highlighted exit-only hypothesis on the independently discovered SHORT retrace entry:

`Low K1 OPP0 -> causal leave -> BLIND F15 -> H2 Low -> downside extension -> E20_DOWN milestone -> causal profit lock / runner`.

This study does **not** change the SHORT detector, F15 zone, entry timing, regime universe, target milestone, or pre-E20 invalidation. It asks only whether post-E20 profit management improves the economics of BLIND_F15.

## Frozen cohort
Use exactly B27AK `F15` rows with `filled=True`.

Required reproduction before interpretation:
- external: 50 fills, 37 H2;
- development: 79 fills, 59 H2;
- reference_validation: 34 fills, 24 H2;
- august: 1 fill, 1 H2.

The B27AN fixed E20/D50 baseline must reproduce before the post-E20 result is interpreted.

## Frozen geometry
For completed previous London session:
- `R = H-L`;
- entry = `F15 = L + 0.15R`;
- pre-E20 close invalidation = `F65 = L + 0.65R` (D50);
- profit milestone = `E20_DOWN = L - 0.20R`.

No F14/F16, alternate stop, alternate target, regime filter, confirmation rule, or additional numeric threshold is allowed.

## Baseline fixed exit
Reproduce B27AN E20/D50:
- target is resting E20_DOWN limit;
- completed 5m `close > F65` invalidates at actual close;
- E20 target touch has intrabar precedence over same-bar close invalidation;
- session-end time exit at first 5m open at/after 20:00 UTC.

## Post-E20 profit-lock rule
Before E20_DOWN is first reached:
- identical F65 completed-close invalidation.

On the first bar whose low reaches E20_DOWN:
- E20 is a **milestone**, not a final TP;
- the full position remains open;
- starting from the next causal 5m bar, a resting SHORT profit ceiling is active at E20_DOWN.

After activation:
1. If a later bar opens at/above the active ceiling, exit at the actual open.
2. Else if its high reaches/exceeds the active ceiling, exit at the ceiling.
3. Otherwise remain open.
4. A strict three-bar pivot high confirmed at a completed bar may ratchet the ceiling **downward only** when that pivot high is below the current ceiling. The new ceiling is effective only from the next bar.
5. Ceiling never rises.
6. If price keeps falling and the ceiling is never hit, remain in the full position until session-end time exit.

This is the exact causal profit-lock concept previously used in the SHORT mirror lineage, now re-audited on the independently discovered B27AK F15 cohort.

## Economics
- illustrative notional: $500;
- round-trip fee: $0.40;
- SHORT gross return = `1 - exit/entry`;
- win = net PnL > 0.

## Outputs
For fixed and profit-lock variants, by partition and pooled-major:
- N;
- WR;
- PF;
- mean expectancy/trade;
- total PnL;
- E20 reach rate;
- median hold.

For profit-lock additionally:
- number of ceiling hits / gap exits / time exits;
- median ratchet count;
- median trough extension after E20;
- median realized exit extension;
- median capture ratio;
- median giveback.

## Frozen support gate
`SUPPORTED` only if the profit-lock variant:
1. has pooled-major expectancy > 0 and PF >= 1.20;
2. beats the reproduced fixed baseline in pooled-major total PnL;
3. has expectancy >= 0 and PF >= 1.00 in each external, development, and reference_validation partition.

If any condition fails, report NOT SUPPORTED. No post-hoc exit variation may be added in B27AQ.

## Mandatory assertions
1. B27AK F15 fill/H2 counts reproduce exactly.
2. Entry equals F15 exactly.
3. B27AN fixed E20/D50 economics reproduce within rounding tolerance before hybrid interpretation.
4. No wick-only F65 invalidation.
5. Profit ceiling is inactive until E20 is reached.
6. E20 activation bar cannot be stopped by the newly activated ceiling; ceiling is effective next bar only.
7. Ceiling can only ratchet downward.
8. Pivot ratchets are causal and effective next bar.
9. No post-session event is used.
10. Full 5m archive coverage reproduces.

Research only; live BBC unchanged.
