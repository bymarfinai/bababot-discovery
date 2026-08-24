# B27DH — F85 LONG 05:30 / 23:30 Zone-Specific Causal Filter Screen — Preregistration

## Purpose
Test whether the two remaining promising raw F85 LONG clock zones can be improved toward ~75% WR without post-hoc threshold rescue, while enforcing the already-frozen global BTC one-position rule.

Zones are frozen from B27DE:
- `ZONE_0530`: reference 05:30–11:00 UTC, execution 11:00–17:30 UTC (`clock_min=330`).
- `ZONE_2330`: reference 23:30–05:00+1d UTC, execution 05:00–11:30+1d UTC (`clock_min=1410`).

The frozen primary blockers are B27DG PRIMARY_2ZONE:
- London (`clock_min=480`) unfiltered Same-Bar F85 LONG.
- ALT_0330 (`clock_min=210`) with B27DF `TOUCH_FIRST_HALF` treatment (`touch_elapsed_min <= 195`).

## Operational rule — frozen
One BTC position maximum. Candidate events are processed causally by entry timestamp. Earliest eligible entry is accepted. Any later candidate with `entry_bar_start < active exit_ts` is skipped. A new entry is allowed only at/after the prior `exit_ts`. Primary setups win exact-timestamp ties according to the already-frozen B27DG tie order.

## Filter information set
Only information available by entry may be used. No future bars, post-entry outcome, indicator mining, or threshold grids.

Execution-window half = 195 minutes, inherited from B27DF. RR threshold 0.50 is inherited from B27DF. These are not optimized in B27DH.

Frozen menu, evaluated separately for each zone:
1. `BASE`
2. `TOUCH_FIRST_HALF`: F85 touch elapsed <=195m from execution start.
3. `TOUCH_SECOND_HALF`: F85 touch elapsed >195m.
4. `K1_FIRST_HALF`: K1 signal timestamp elapsed <=195m from execution start.
5. `K1_SECOND_HALF`: K1 signal timestamp elapsed >195m.
6. `RR_GE_050`: nominal RR >=0.50.
7. `TOUCH_FIRST_HALF__RR_GE_050`
8. `TOUCH_SECOND_HALF__RR_GE_050`
9. `K1_FIRST_HALF__TOUCH_FIRST_HALF`
10. `K1_SECOND_HALF__TOUCH_SECOND_HALF`

No 4H regime filter is included because B27DF did not establish NO_BEAR as a useful generic discriminator and prior B27AG showed SIDEWAYS can be strong for F85 LONG.

## Development selection — frozen
Each candidate treatment is combined with PRIMARY_2ZONE and passed through the global one-position lock before scoring the added zone.

A non-BASE treatment is `DEV_75_ELIGIBLE` only if the added zone, after lock, has:
- accepted N >=20
- accepted retention >=60% of that zone's raw development candidates
- WR >=75%
- PF >=1.30
- expectancy >0

If multiple qualify, rank by WR, PF, expectancy, accepted retention, fewer filter components, then lexical name.

If none qualify, report the best non-BASE treatment satisfying N>=20, retention>=60%, PF>=1.20, expectancy>0 as `BEST_BELOW_75`. This is descriptive only and cannot be promoted by B27DH.

## Historical replication — frozen
Only a `DEV_75_ELIGIBLE` selection can be replication-supported. The same treatment is then scored after the same portfolio lock in reused historical partitions.

Both external and reference_validation must independently satisfy:
- accepted N >=10
- accepted retention >=45% of raw zone candidates
- WR >=70%
- PF >=1.20
- expectancy >0

These are historical replication checks, not pristine fresh OOS.

## Portfolio reporting
For each zone, report the 3-zone portfolio (PRIMARY_2ZONE + that zone's selected treatment) by partition.

Then report:
- `PROMOTED_PORTFOLIO`: PRIMARY_2ZONE plus only B27DH zones with replication_supported=TRUE.
- `EXPLORATORY_SELECTED_PORTFOLIO`: PRIMARY_2ZONE plus both selected B27DH treatments regardless of promotion, clearly labeled exploratory.

No live BBC change is authorized by this experiment.
