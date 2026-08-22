# B27AT — BTC London->NY SHORT BLIND_F15 Full-Position Hybrid Activation Grid — Preregistration

## Purpose
Test the user's intended SHORT analogue of the LONG B27AC hybrid: the milestone is only a profit-lock activation boundary; **100% of the position remains open for continuation after activation**. Search the activation level once over a frozen grid already present in the downside-extension atlas.

Frozen structure:
**Low K1 OPP0 -> causal leave -> BLIND F15 -> downside activation milestone -> keep 100% open -> causal profit-ceiling runner.**

## Frozen cohort
Use exactly the B27AK/B27AN BLIND_F15 filled cohort:
- external 50
- development 79
- reference_validation 34
- august 1

Entry = F15 = L + 0.15R. No confirmation filter and no regime gate.

## Pre-activation risk
Use frozen B27AN D50 boundary:
- F65 = L + 0.65R
- invalidation only on completed raw 5m close strictly above F65
- exit at that actual completed close
- wick-only penetration does not invalidate.

## Frozen activation grid
Use only already-defined atlas levels:
- E05 = L - 0.05R
- E10 = L - 0.10R
- E15 = L - 0.15R
- E20 = L - 0.20R
- E25 = L - 0.25R
- E30 = L - 0.30R
- E40 = L - 0.40R
- E50 = L - 0.50R

No E07/E12/intermediate activation may be introduced after results.

## Full-position hybrid runner
At first intrabar touch of the chosen activation milestone:
- **no partial TP is taken**;
- **100% of the original $500 illustrative position stays open**;
- the milestone becomes the initial resting profit ceiling for the SHORT from the NEXT raw 5m bar;
- if next/later bar open >= ceiling, exit 100% at actual open;
- else if high >= ceiling, exit 100% at ceiling;
- otherwise continue holding;
- a strict 3-bar pivot high centered on the prior bar becomes known only at current bar close and may ratchet the ceiling DOWN for the next bar if that pivot high is below the active ceiling;
- ceiling never rises;
- no F65 stop remains after activation;
- if no ceiling exit occurs by NY session end, exit 100% at the exact session-end open.

If activation is touched intrabar on a bar that later closes above F65, activation happens first chronologically and the later close does not retroactively invalidate it.

## Economics
- illustrative notional $500
- round-trip fee $0.40 once per trade
- no split legs.

## Frozen selection rule
A candidate is **supported/eligible** only if:
1. pooled-major expectancy > 0;
2. pooled-major PF >= 1.20;
3. pooled-major total PnL is better than frozen B27AN fixed E20/D50 pooled-major baseline;
4. in EACH external/development/reference_validation partition: expectancy >= 0 and PF >= 1.0.

Among supported candidates, select the one with highest pooled-major total net PnL. If none is supported, selected activation = NONE. Also report the highest-pooled-PnL candidate as diagnostic only; it is not promoted if it fails the gate.

## Mandatory assertions
1. B27AK/B27AN BLIND_F15 identities reproduce exactly 50/79/34/1.
2. Frozen B27AN E20/D50 fixed baseline reproduces before interpretation.
3. E20 full-position hybrid reproduces B27AQ before other activation levels are interpreted.
4. Activation geometry is exact for E05/E10/E15/E20/E25/E30/E40/E50.
5. No position reduction occurs at activation.
6. Pre-activation invalidation is completed-close F65 only.
7. Intrabar activation precedes same-bar completed-close F65 invalidation.
8. Profit ceiling is effective only from the next bar.
9. Ceiling can only ratchet downward.
10. No regime, confirmation, alternate entry, alternate stop, partial split, candle threshold, or new numeric level is introduced.

Research only. Live BBC unchanged.
