# BTC Temporal Saturday T-Method S5.7C — Hinge Rejection Robustness × Management Interaction

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — MORPHOLOGY ROBUSTNESS PASS; NEW MANAGEMENT ACTION NOT ELIGIBLE  
**Research only:** live BBC untouched

## Frozen candidate
`REJECTED_HINGE = first +0.50 hinge candle upper wick >=50% of full candle range`.

No wick/body threshold sweep. No new cut, protect, partial TP, sizing, delay, or A7.19 override is applied.

## Frozen parity
- Static parent all 139: **+$87.200**
- A7.19 all 139: **+$103.383**
- +0.50 hinge trades: **89** = 61 future-deep / 28 shallow
- Exact S5.7B rejected-hinge cohort: **16**, with **7 deep / 9 shallow** = **43.75% deep**

## Rejected vs accepted hinge
### REJECTED_HINGE
- N **16**
- future deep **43.75%**
- parent WR **56.25%**
- parent PnL **+$37.015**
- A7.19 PnL **+$36.946**
- A7.19 uplift vs parent **-$0.069**
- median parent MFE **+0.706%**
- median parent MAE **0.345%**
- A7.19 actions **2**

Discovery:
- N10 / deep **40.0%**
- parent **+$21.893**
- A7.19 **+$21.824**

Validation:
- N6 / deep **50.0%**
- parent = A7.19 **+$15.121**

### ACCEPTED_HINGE
- N **73**
- future deep **73.97%**
- parent WR **73.97%**
- parent PnL **+$212.624**
- A7.19 PnL **+$228.876**
- A7.19 uplift vs parent **+$16.252**
- median parent MFE **+1.201%**
- median parent MAE **0.381%**
- A7.19 actions **6**

Discovery:
- N44 / deep **77.27%**
- parent **+$137.901**
- A7.19 **+$151.891**

Validation:
- N29 / deep **68.97%**
- parent **+$74.723**
- A7.19 **+$76.985**

## Four chronological folds
Using fixed quarters of the original 139-Saturday chronology:

1. idx 0–34: rejected N2 / **100% deep** vs accepted N20 / **90% deep** → direction fails, but rejected N is only 2
2. idx 35–69: rejected N7 / **28.57% deep** vs accepted N17 / **70.59% deep** → expected direction
3. idx 70–104: rejected N2 / **0% deep** vs accepted N14 / **57.14% deep** → expected direction
4. idx 105–138: rejected N5 / **60.0% deep** vs accepted N22 / **72.73% deep** → expected direction

Expected direction holds in **3/4 comparable folds**.

**Morphology robustness gate: PASS.**

The first fold is the only reversal and has only two rejected observations, so it is not enough to overturn the D/V + 3/4-fold evidence. It does, however, argue against treating rejection as a deterministic failure label.

## A7.19 interaction — important result
Among +0.50 hinge trades there are the exact **8 A7.19 actions**.

- rejected hinge: **2 / 16** actions
- accepted hinge: **6 / 73** actions

For the two rejected A7.19-action trades:
- parent PnL **+$1.437**
- A7.19 **+$1.368**
- A7.19 actually changes economics by only **-$0.069**

For the six accepted A7.19-action trades:
- parent **-$12.130**
- A7.19 **+$4.122**
- uplift **+$16.252**

Therefore the full A7.19 improvement is concentrated in accepted-hinge trades, not rejected-hinge trades.

This is a key distinction:
> hinge upper-wick rejection predicts lower future excursion quality, but it is not the state that A7.19 monetization is fixing.

A7.19 and hinge morphology are measuring different things.

## A7.26 overlap / orthogonality
- rejected + pre-entry STRETCHED: only **2 / 16 rejected trades**
- total STRETCHED among +0.50 hinge trades: **9 / 89**
- rejected but NOT stretched: **14 trades**, deep **42.86%**, A7.19 PnL **+$35.470**

Therefore hinge rejection is largely **orthogonal** to A7.26 pre-entry exhaustion. It is not merely a re-expression of the existing STRETCHED state.

Conceptually:
- A7.26 STRETCHED = weakness/exhaustion already present before entry.
- S5.7C REJECTED_HINGE = post-entry proof-of-strength is rejected when +0.50 is first reached.

These are separate information dimensions.

## Economic guardrail
Despite substantially lower deep-runner probability, REJECTED_HINGE remains profitable:
- full A7.19 **+$36.946**
- discovery **+$21.824**
- validation **+$15.121**

Therefore:
> lower deep probability does NOT imply the rejected cohort should be cut or excluded.

The predeclared new-management gate required rejected-hinge A7.19 economics to be nonpositive in both discovery and validation. It fails clearly.

**New management action eligible: NO.**

## S5.7C verdict
**PASS as a robust adaptive confidence dimension; FAIL as a standalone failure-management trigger.**

What survives:
> `+0.50 hinge + dominant upper wick` is a robust sign of weaker runner acceptance / lower excursion potential.

What does not follow:
> it should NOT automatically trigger cut, protect, A7.19 override, or skip.

The useful adaptive interpretation is confidence-state information:
- ACCEPTED_HINGE = stronger runner quality / higher excursion potential.
- REJECTED_HINGE = lower runner quality, but still economically positive under current management.

A7.19 remains the official full-coverage Saturday champion. A7.26 remains the preserved selective benchmark.
