# BNB B41-S6E-L — LONG Recovery-Test Exit Rule

**Status: BNB_B41_S6E_L_LONG_RECOVERY_INVALIDATION_NOT_READY**

S6E-L signature: `953f2a9a1a721fbe0c8fcefcaa73feb4470ae72e7407b9e4cb14aab4f4b7a5e8`

The +60m 2-of-3 signal is treated as an alarm. Only failed recovery exits; recovered alarms hold to detector+180m.

## Policy audit

| Period | Policy | Alarms W/L | Exits | False-stop | Alarm winner preserved | Alarm loser caught | Med loser improve | Mean Δ | q10 Δ | Positive |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | E1_45M_WALL_RECLAIM | 6/8 | 7 | 1/49 (2.0%) | 83.3% | 75.0% | -0.008x | -0.006x | -0.020x | 63.2% |
| DEV | E2_60M_POSITIVE_PROGRESS | 6/8 | 5 | 0/49 (0.0%) | 100.0% | 62.5% | -0.097x | -0.013x | -0.079x | 64.5% |
| REF | E1_45M_WALL_RECLAIM | 2/8 | 7 | 0/24 (0.0%) | 100.0% | 87.5% | -0.049x | -0.011x | -0.035x | 57.1% |
| REF | E2_60M_POSITIVE_PROGRESS | 2/8 | 7 | 1/24 (4.2%) | 50.0% | 75.0% | -0.085x | -0.022x | -0.023x | 54.8% |
| ALL | E1_45M_WALL_RECLAIM | 8/16 | 14 | 1/73 (1.4%) | 87.5% | 81.2% | -0.049x | -0.008x | -0.030x | 61.0% |
| ALL | E2_60M_POSITIVE_PROGRESS | 8/16 | 12 | 1/73 (1.4%) | 87.5% | 68.8% | -0.097x | -0.016x | -0.050x | 61.0% |

## DEV gate

| Policy | Eligible |
|---|---|
| E1_45M_WALL_RECLAIM | NO |
| E2_60M_POSITIVE_PROGRESS | NO |

## Nomination
- DEV nominee: **NO_NOMINATION**.
- REF validated: **NO**.
- LONG recovery invalidation: **NOT READY**.

No TP, WR optimization, PF, expectancy, leverage, fees/slippage optimization, or PnL optimization.
