# BNB B41-S6F-L — Failed-Recovery Exit Path Anatomy

**Status: BNB_B41_S6F_L_NO_STABLE_FAILED_RECOVERY_BOUNCE_MECHANISM**

S6F-L signature: `d62c788c66afee53a9c6d09fb0fb9e4b5f00d96caa22bafc5c3a34b53e0d2ed4`

Cohort is frozen to E1_45M_WALL_RECLAIM failures. S6F-L studies executable post-failure bounce opportunities; it does not create an exit rule.

## Failed-recovery cohort
- DEV: 7 total failed recoveries, 6 baseline losers, 1 baseline winner.
- REF: 7 total failed recoveries, 7 baseline losers, 0 baseline winners.

## Baseline-loser exit-path audit

| Type | Probe/checkpoint | Period | N | Fill | Med improve vs immediate | > immediate | Med improve vs endpoint | Event min |
|---|---|---|---:|---:|---:|---:|---:|---:|
| FIXED_WAIT | WAIT_5M | DEV | 6 | 100.0% | 0.008x | 66.7% | -0.018x | 5.000x |
| FIXED_WAIT | WAIT_5M | REF | 7 | 100.0% | 0.017x | 57.1% | -0.049x | 5.000x |
| FIXED_WAIT | WAIT_5M | ALL | 13 | 100.0% | 0.015x | 61.5% | -0.049x | 5.000x |
| FIXED_WAIT | WAIT_10M | DEV | 6 | 100.0% | -0.038x | 33.3% | -0.033x | 10.000x |
| FIXED_WAIT | WAIT_10M | REF | 7 | 100.0% | -0.029x | 42.9% | -0.066x | 10.000x |
| FIXED_WAIT | WAIT_10M | ALL | 13 | 100.0% | -0.029x | 38.5% | -0.060x | 10.000x |
| FIXED_WAIT | WAIT_15M | DEV | 6 | 100.0% | -0.132x | 0.0% | -0.062x | 15.000x |
| FIXED_WAIT | WAIT_15M | REF | 7 | 100.0% | 0.017x | 57.1% | -0.068x | 15.000x |
| FIXED_WAIT | WAIT_15M | ALL | 13 | 100.0% | -0.053x | 30.8% | -0.068x | 15.000x |
| FIXED_WAIT | WAIT_30M | DEV | 6 | 100.0% | 0.042x | 66.7% | -0.102x | 30.000x |
| FIXED_WAIT | WAIT_30M | REF | 7 | 100.0% | 0.050x | 71.4% | -0.058x | 30.000x |
| FIXED_WAIT | WAIT_30M | ALL | 13 | 100.0% | 0.050x | 69.2% | -0.064x | 30.000x |
| FIXED_WAIT | WAIT_45M | DEV | 6 | 100.0% | -0.061x | 50.0% | -0.148x | 45.000x |
| FIXED_WAIT | WAIT_45M | REF | 7 | 100.0% | 0.069x | 100.0% | 0.016x | 45.000x |
| FIXED_WAIT | WAIT_45M | ALL | 13 | 100.0% | 0.046x | 76.9% | -0.037x | 45.000x |
| FIXED_WAIT | WAIT_60M | DEV | 6 | 100.0% | -0.003x | 50.0% | -0.062x | 60.000x |
| FIXED_WAIT | WAIT_60M | REF | 7 | 100.0% | 0.049x | 57.1% | -0.036x | 60.000x |
| FIXED_WAIT | WAIT_60M | ALL | 13 | 100.0% | 0.049x | 53.8% | -0.036x | 60.000x |
| PROBE | FIRST_CLOSE_ABOVE_FAILURE_30 | DEV | 6 | 100.0% | 0.015x | 100.0% | 0.008x | 5.000x |
| PROBE | FIRST_CLOSE_ABOVE_FAILURE_30 | REF | 7 | 71.4% | 0.042x | 100.0% | -0.066x | 5.000x |
| PROBE | FIRST_CLOSE_ABOVE_FAILURE_30 | ALL | 13 | 84.6% | 0.017x | 100.0% | -0.037x | 5.000x |
| PROBE | FIRST_WALL_TOUCH_60 | DEV | 6 | 0.0% | — | — | — | — |
| PROBE | FIRST_WALL_TOUCH_60 | REF | 7 | 14.3% | 0.166x | 100.0% | -0.102x | 15.000x |
| PROBE | FIRST_WALL_TOUCH_60 | ALL | 13 | 7.7% | 0.166x | 100.0% | -0.102x | 15.000x |
| PROBE | FIRST_WALL_CLOSE_60 | DEV | 6 | 0.0% | — | — | — | — |
| PROBE | FIRST_WALL_CLOSE_60 | REF | 7 | 14.3% | 0.231x | 100.0% | -0.037x | 45.000x |
| PROBE | FIRST_WALL_CLOSE_60 | ALL | 13 | 7.7% | 0.231x | 100.0% | -0.037x | 45.000x |

## DEV bounce candidates

| Type | Candidate | DEV fill | REF fill | DEV vs immediate | REF vs immediate | DEV vs endpoint | REF vs endpoint | REF consistent |
|---|---|---:|---:|---:|---:|---:|---:|---|
| PROBE | FIRST_CLOSE_ABOVE_FAILURE_30 | 100.0% | 71.4% | 0.015x | 0.042x | 0.008x | -0.066x | NO |

## Stable mechanisms

- None.

## Gate
- DEV bounce candidates: **1**.
- REF-directionally-consistent: **0**.
- Next step: **do not add a post-failure bounce exit rule**.

No TP, EMA/Fibonacci, leverage, PF, expectancy, fees/slippage optimization, or PnL optimization.
