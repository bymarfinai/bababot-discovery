# BNB B41-S6E-L — LONG Recovery-Test Exit Rule Preregistration

## Objective

Turn the frozen S6C-L alarm plus S6D-L recovery anatomy into a finite causal exit policy.

The alarm is not an exit. A trade that alarms at +60m gets one fixed recovery test. If it fails that test, exit at the recovery checkpoint close. If it passes, hold to the frozen detector+180m endpoint.

## Frozen parents

- S6C-L signature: `75fac38b1ff31e8fc29003ba87109c66ca6da27b9f011c68044aaee21546aa8f`
- S6D-L signature: `fc4ec7581c282e2f61f578df00ace715451381b92d15c82453d56f369e33281a`
- Setup: LOWER Q80 + TF60 C2 reclaim -> MARKET LONG.
- Alarm: `R4_60_2OF3_Q85` at detector+60m.
- No alarm -> hold unchanged to detector+180m.
- No re-entry.
- No EMA/Fibonacci.

## Frozen recovery policies

### E1_45M_WALL_RECLAIM
For an alarmed trade:
- wait 45 minutes after the alarm (detector+105m);
- recovery PASS if the completed 5m close is at or above the frozen Q80 wall;
- recovery FAIL otherwise;
- FAIL exits at the detector+105m completed close;
- PASS holds to detector+180m.

### E2_60M_POSITIVE_PROGRESS
For an alarmed trade:
- wait 60 minutes after the alarm (detector+120m);
- recovery PASS if the completed close is above the alarm close;
- recovery FAIL otherwise;
- FAIL exits at detector+120m completed close;
- PASS holds to detector+180m.

No other threshold is searched.

## Outcome accounting

For a failed recovery exit:
`aligned_outcome = (exit - entry) / wall_distance`.

For all other trades:
use frozen +180m aligned outcome.

Metrics:
- overall false-stop winner rate;
- overall loser catch rate;
- alarm-conditioned loser catch rate;
- alarm-conditioned winner preservation rate;
- median improvement among caught losers;
- mean outcome delta vs baseline;
- q10 outcome delta vs baseline;
- positive-outcome rate.

## DEV eligibility

A policy is DEV_ELIGIBLE if:
- baseline n180 >=30;
- overall false-stop winner rate <=10%;
- alarm-conditioned winner preservation >=80%;
- alarm-conditioned loser catch >=50%;
- median caught-loser improvement >0;
- mean managed outcome >= baseline mean;
- q10 managed outcome > baseline q10.

The conditional loser-catch gate is intentional: S6E-L only manages the frozen R4 alarm cohort. It does not redefine which trades are alarmed.

## DEV nomination

Choose the earliest DEV_ELIGIBLE recovery checkpoint:
E1 45m before E2 60m.

If none qualifies -> NO_NOMINATION.

## REF holdout

The single DEV nominee validates if:
- baseline n180 >=20;
- overall false-stop winner rate <=10%;
- alarm-conditioned winner preservation >=80%;
- alarm-conditioned loser catch >=50%;
- median caught-loser improvement >0;
- mean managed outcome >= REF baseline mean;
- q10 managed outcome > REF baseline q10.

No substitute after REF.

## Gate

Validated nominee -> `LONG_RECOVERY_INVALIDATION_READY`.

Otherwise -> `LONG_RECOVERY_INVALIDATION_NOT_READY`.

No TP, WR optimization, PF, expectancy, leverage, fees/slippage optimization, or PnL optimization.
