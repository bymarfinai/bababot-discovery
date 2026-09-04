# SOL LONG 15:00 UTC Confirmed-Recovery Retest Anatomy — A35 Preregistration

## Context
A34 showed the strongest delayed-confirmation lane (`DC10_C12`) reached ~59% recovery WR but had poor payoff because median entry was ~H+0.17R. A35 is forensic only: it asks whether the confirmed continuation often offers a cheaper retest before E40.

## Frozen cohort
Use the exact `DC10_C12` state:
1. frozen R360 / 15:00 UTC parent loses;
2. RC30_C2 second close > H occurs within 30m after parent exit;
3. no E40 before the signal;
4. H is not lost during the next two completed bars;
5. the +10m completed close after the RC30_C2 signal is >= H+0.12R;
6. no E40 before that +10m confirmation close.

No trade is entered in A35.

## Fixed post-confirmation anatomy
Observe causally from the completed +10m confirmation close until E40, close<=H failure, or frozen recovery-window end.

Measure:
- eventual E40 continuation;
- first touch of E10 = H+0.10R;
- first touch of E05 = H+0.05R;
- first touch of H;
- time to those retests;
- minimum low and close in R units before E40/failure;
- maximum extension from H before E40/failure;
- whether E10/E05 retest occurs before E40;
- whether a retest is followed by E40 before H failure.

Primary candidate level is **E10**, because 0.10R is already frozen by A28/A33/A34 and approximately matches the successful immediate-recovery entry geometry from A30. E05 is diagnostic only and cannot be promoted unless E10 is clearly inadequate and E05 replication is materially stronger.

## Support requirement for A36
A35 may authorize one fixed confirmed-retest entry only if, in Central Development:
- confirmed cohort N >= 25;
- eventual E40 cohort N >= 10;
- at least 40% of eventual E40 continuations retest E10 before E40;
- E10-retest->E40 rate is economically material (>=35%);
- the direction of E10 retest opportunity is not contradicted in Central External and Central Reference Validation;
- at least 3/4 topology support rows show non-zero E10 retest opportunity among eventual E40 continuations.

A35 is anatomy only. No threshold/window scan and no OOS retuning.

Research only. Live Baba Bot remains unchanged.
