# BNB Session-Native LONG M8 MICRO_HL_BULL Loss Anatomy — B27ET Result

Raw BNB 5m coverage: **100.0000%**.

Frozen setup: **E5_MICRO_HL_BULL**, TP **H+0.30R**, SL **0.30R**, total cost **0.15%**. Development only.

Integrity: **50 trades = 25 net winners + 25 net losers**; exits = **19 TP + 20 SL + 11 session close**; same-bar TP/SL collisions = **0**.

## Loss path breakdown

| Loss path | Count | Share losses | Median exit time | Median pre-exit MFE | Median PnL @ $500 |
|---|---:|---:|---:|---:|---:|
| SL_BEFORE_H | 16 | 64.0% | 40.0m | 0.148R | $-3.71 |
| CLOSE_LOSS_BEFORE_H | 3 | 12.0% | 95.0m | 0.021R | $-1.43 |
| SL_AFTER_H_BEFORE_H10 | 3 | 12.0% | 105.0m | 0.103R | $-2.57 |
| COST_FLIP_CLOSE | 2 | 8.0% | 325.0m | 0.375R | $-0.63 |
| SL_AFTER_H10_BEFORE_H20 | 1 | 4.0% | 140.0m | 0.417R | $-4.89 |

## What losers did before failing

- Hard-stop exits among net losers: **20/25 (80.0%)**.
- Session-close exits among net losers: **5/25 (20.0%)**.
- Reached H on a completed bar strictly before exit: **6/25 (24.0%)**.
- Reached H+0.10R strictly before exit: **3/25 (12.0%)**.
- Reached H+0.20R strictly before exit: **0/25 (0.0%)**.
- Net losses resolved within <=15 minutes: **5/25 (20.0%)**.
- Gross-positive close trades flipped negative only by costs: **2**.

## Strongest causal pre-entry descriptive differences

| Rank | Feature | Winner median | Loser median | P(loss > win) |
|---:|---|---:|---:|---:|
| 1 | pre_entry_max_close_depth_R | 0.2297 | 0.4141 | 68.2% |
| 2 | signal_low_depth_R | 0.2841 | 0.4564 | 67.5% |
| 3 | entry_depth_R | 0.1527 | 0.3495 | 66.7% |
| 4 | pre_entry_max_depth_R | 0.3328 | 0.5199 | 66.7% |
| 5 | prev_low_depth_R | 0.3328 | 0.4966 | 66.4% |
| 6 | signal_range_R | 0.1038 | 0.1405 | 66.1% |
| 7 | minutes_entry_to_ny_close | 350.0000 | 320.0000 | 37.3% |
| 8 | minutes_ny_open_to_entry | 40.0000 | 70.0000 | 62.7% |

Common-language effect size is descriptive only: 50% means no directional separation; values far above 50% mean losses tend to have larger feature values, far below 50% mean losses tend to have smaller values.

No threshold/filter is selected or promoted from this milestone.

**Status: B27ET_BNB_MICROHL_LOSS_ANATOMY_COMPLETE**

STOP: no filter selection, no TP/SL retuning, no holdout reveal, no August, no SHORT/live integration.
