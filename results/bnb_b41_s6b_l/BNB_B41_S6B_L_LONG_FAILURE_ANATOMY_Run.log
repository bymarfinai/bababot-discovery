# BNB B41-S6B-L — LONG Failure Anatomy

**Status: BNB_B41_S6B_L_LONG_FAILURE_PRECURSOR_FOUND**

S6B-L signature: `35ab7d201fe45d398b3c959483aa7eef5d68a9d901336d57a25489f9b2f54190`

Setup is frozen: Lower Q80 reclaim, TF60 maturation, market LONG. S6B-L discovers precursors only; it does not create an SL.

## DEV-nominated precursor validation

| Horizon | Feature | Kind | DEV strength | REF strength | DEV nominated | REF validated |
|---:|---|---|---:|---:|---|---|
| 15m | mae_so_far | CONT | 0.605 | 0.560 | YES | YES |
| 30m | down_slope_3 | CONT | 0.637 | 0.692 | YES | YES |
| 30m | entry_drawdown | CONT | 0.692 | 0.623 | YES | YES |
| 30m | lack_mfe | CONT | 0.635 | 0.500 | YES | NO |
| 30m | mae_so_far | CONT | 0.664 | 0.586 | YES | YES |
| 45m | entry_drawdown | CONT | 0.693 | 0.606 | YES | YES |
| 45m | lack_mfe | CONT | 0.679 | 0.542 | YES | NO |
| 45m | lower_low_pressure | CONT | 0.650 | 0.458 | YES | NO |
| 45m | mae_so_far | CONT | 0.695 | 0.602 | YES | YES |
| 60m | below_wall_fraction | CONT | 0.618 | 0.556 | YES | YES |
| 60m | down_slope_3 | CONT | 0.657 | 0.704 | YES | YES |
| 60m | entry_drawdown | CONT | 0.766 | 0.718 | YES | YES |
| 60m | lack_mfe | CONT | 0.691 | 0.574 | YES | YES |
| 60m | lower_low_pressure | CONT | 0.649 | 0.609 | YES | YES |
| 60m | mae_so_far | CONT | 0.701 | 0.620 | YES | YES |
| 60m | max_consecutive_below_wall | CONT | 0.615 | 0.557 | YES | YES |

## REF-validated stable precursors

| Horizon | Feature | Kind | DEV | REF |
|---:|---|---|---:|---:|
| 15m | mae_so_far | CONT | 0.605 | 0.560 |
| 30m | down_slope_3 | CONT | 0.637 | 0.692 |
| 30m | entry_drawdown | CONT | 0.692 | 0.623 |
| 30m | mae_so_far | CONT | 0.664 | 0.586 |
| 45m | entry_drawdown | CONT | 0.693 | 0.606 |
| 45m | mae_so_far | CONT | 0.695 | 0.602 |
| 60m | below_wall_fraction | CONT | 0.618 | 0.556 |
| 60m | down_slope_3 | CONT | 0.657 | 0.704 |
| 60m | entry_drawdown | CONT | 0.766 | 0.718 |
| 60m | lack_mfe | CONT | 0.691 | 0.574 |
| 60m | lower_low_pressure | CONT | 0.649 | 0.609 |
| 60m | mae_so_far | CONT | 0.701 | 0.620 |
| 60m | max_consecutive_below_wall | CONT | 0.615 | 0.557 |

## Detector-extreme CLOSE5 breach anatomy (descriptive only)

| Period | Breach cohort | N | Time to breach | Prior close vs wall | Pre MAE | Pre MFE | Below-wall frac | Reclaims | Failed reclaims |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | FALSE_BREACH_WINNER | 5 | 75.000m | -0.047x | 0.200x | 0.078x | 12.5% | 0.000 | 1.000 |
| DEV | TRUE_FAILURE_LOSER | 10 | 107.500m | -0.099x | 0.335x | 0.134x | 26.7% | 1.000 | 2.000 |
| REF | FALSE_BREACH_WINNER | 3 | 70.000m | 0.041x | 0.186x | 0.269x | 0.0% | 0.000 | 0.000 |
| REF | TRUE_FAILURE_LOSER | 9 | 50.000m | -0.026x | 0.147x | 0.120x | 9.4% | 0.000 | 1.000 |
| ALL | FALSE_BREACH_WINNER | 8 | 72.500m | -0.041x | 0.193x | 0.107x | 8.6% | 0.000 | 1.000 |
| ALL | TRUE_FAILURE_LOSER | 19 | 80.000m | -0.064x | 0.276x | 0.120x | 18.2% | 1.000 | 2.000 |

## Gate
- Stable REF-validated precursor count: **13**.
- Earliest stable precursor horizon: **15m**.
- Next step: **S6C-L causal invalidation rule construction**.

No SL threshold, TP, trade WR, PF, expectancy, leverage, or PnL was optimized.
