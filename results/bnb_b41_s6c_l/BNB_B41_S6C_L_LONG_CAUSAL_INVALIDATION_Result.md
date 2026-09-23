# BNB B41-S6C-L — LONG Causal Invalidation Rule Construction

**Status: BNB_B41_S6C_L_LONG_INVALIDATION_NOT_READY**

S6C-L signature: `75fac38b1ff31e8fc29003ba87109c66ca6da27b9f011c68044aaee21546aa8f`

Thresholds are frozen from DEV winners only. EMA/Fibonacci are excluded. No TP is used.

## Frozen DEV-winner thresholds

| Threshold | Value |
|---|---:|
| score30_q85 | 0.435516 |
| score60_q85 | 0.564036 |
| draw60_q85 | 0.117303 |
| mae60_q85 | 0.227402 |
| slope60_q85 | 0.098555 |

## Rule audit

| Period | Candidate | Stops | False-stop winners | Loser catch | Med loser improve | Mean Δ | q10 Δ | Positive | Med stop outcome |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | R1_30_SCORE_Q85 | 22.4% | 8/49 (16.3%) | 9/27 (33.3%) | 0.110x | -0.020x | 0.054x | 55.3% | -0.110x |
| DEV | R2_60_DRAW_Q85 | 22.4% | 8/49 (16.3%) | 9/27 (33.3%) | 0.125x | -0.024x | 0.024x | 53.9% | -0.195x |
| DEV | R3_60_SCORE_Q85 | 21.1% | 8/49 (16.3%) | 8/27 (29.6%) | 0.108x | -0.034x | 0.012x | 53.9% | -0.186x |
| DEV | R4_60_2OF3_Q85 | 18.4% | 6/49 (12.2%) | 8/27 (29.6%) | 0.136x | -0.019x | 0.012x | 56.6% | -0.201x |
| REF | R1_30_SCORE_Q85 | 38.1% | 8/24 (33.3%) | 8/18 (44.4%) | 0.217x | -0.055x | 0.225x | 38.1% | -0.128x |
| REF | R2_60_DRAW_Q85 | 26.2% | 3/24 (12.5%) | 8/18 (44.4%) | 0.087x | -0.004x | 0.150x | 50.0% | -0.283x |
| REF | R3_60_SCORE_Q85 | 28.6% | 4/24 (16.7%) | 8/18 (44.4%) | 0.087x | -0.032x | 0.150x | 47.6% | -0.280x |
| REF | R4_60_2OF3_Q85 | 23.8% | 2/24 (8.3%) | 8/18 (44.4%) | 0.087x | -0.001x | 0.150x | 52.4% | -0.294x |
| ALL | R1_30_SCORE_Q85 | 28.0% | 16/73 (21.9%) | 17/45 (37.8%) | 0.177x | -0.032x | 0.147x | 49.2% | -0.116x |
| ALL | R2_60_DRAW_Q85 | 23.7% | 11/73 (15.1%) | 17/45 (37.8%) | 0.116x | -0.017x | 0.046x | 52.5% | -0.220x |
| ALL | R3_60_SCORE_Q85 | 23.7% | 12/73 (16.4%) | 16/45 (35.6%) | 0.087x | -0.034x | 0.046x | 51.7% | -0.220x |
| ALL | R4_60_2OF3_Q85 | 20.3% | 8/73 (11.0%) | 16/45 (35.6%) | 0.100x | -0.012x | 0.046x | 55.1% | -0.247x |

## DEV gate

| Candidate | Eligible |
|---|---|
| R1_30_SCORE_Q85 | NO |
| R2_60_DRAW_Q85 | NO |
| R3_60_SCORE_Q85 | NO |
| R4_60_2OF3_Q85 | NO |

## Nomination
- DEV nominee: **NO_NOMINATION**.
- REF validated: **NO**.
- LONG invalidation gate: **NOT READY**.

No TP, trade WR, PF, expectancy, leverage, or PnL was optimized.
