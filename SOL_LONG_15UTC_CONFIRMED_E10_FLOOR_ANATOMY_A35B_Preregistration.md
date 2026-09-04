# SOL LONG 15:00 UTC Confirmed E10 Close-Floor Anatomy — A35B Preregistration

## Purpose
A35 showed confirmed E40 winners rarely retest E10 in Development while failed confirmations fall much deeper. A35B asks one narrow causal question before any strategy change:

> After exact DC10_C12 confirmation, does a completed close at or below E10 = H+0.10R mostly identify future failure while preserving eventual E40 continuations?

## Frozen cohort
Use the exact A35 DC10_C12 confirmed cohort. No new market state, threshold, or window is introduced.

## Fixed feature
For each cohort row, use the already persisted `min_close_R` from after the completed +10m confirmation until E40, H-failure, or frozen time end.

Define:
- `E10_CLOSE_VIOLATION = min_close_R <= 0.10`.

Measure separately for eventual E40 and non-E40 cohorts across Central Development, Central External, Central Reference Validation, and topology supports.

## Authorization gate for A36
A36 may test a close-based E10 recovery floor only if:
- Central Development eventual-E40 N >= 10;
- <=20% of Central Development eventual-E40 winners violate E10 by close;
- >=50% of Central Development non-E40 cases violate E10 by close;
- failure violation rate exceeds winner violation rate in Central External and Central Reference Validation;
- at least 3/4 External/Reference-Validation topology support rows have failure violation rate > winner violation rate.

No E05/E12/E15 grid. E10 is the only authorized level because it is already frozen from A28/A33/A34.

Research only. Live Baba Bot remains unchanged.
