# BNB B41-S6 — Structural Invalidation / SL Discovery

**Status: BNB_B41_S6_STRUCTURAL_INVALIDATION_NOT_READY**

S6 signature: `cd192358bb7b294fb3f581aa1e887aa7f4de97a4995dae7866b1a440fe3561fc`

No fixed-% stop and no TP are used. Baseline is the frozen S5 market entry held to detector+180m.

## Structural invalidation audit

| Period | Side | Dir | TF | Candidate | Stops | Stop min | False-stop winners | Loser catch | Med loser improve | Mean Δ vs base | q10 Δ vs base | Positive |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | UPPER | SHORT | TF05 | D0_WALL_TOUCH | 84.4% | 5.000xm | 51/67 (76.1%) | 41/42 (97.6%) | 0.178x | -0.074x | 0.380x | 14.7% |
| DEV | UPPER | SHORT | TF05 | S1_WALL_CLOSE5 | 73.4% | 20.000xm | 39/67 (58.2%) | 41/42 (97.6%) | 0.136x | -0.070x | 0.296x | 25.7% |
| DEV | UPPER | SHORT | TF05 | S2_WALL_ACCEPT2 | 63.3% | 40.000xm | 31/67 (46.3%) | 38/42 (90.5%) | 0.145x | -0.055x | 0.212x | 33.0% |
| DEV | UPPER | SHORT | TF05 | S3_WALL_CLOSE15 | 64.2% | 30.000xm | 30/67 (44.8%) | 40/42 (95.2%) | 0.107x | -0.050x | 0.240x | 33.9% |
| DEV | UPPER | SHORT | TF05 | S4_DETECTOR_EXTREME_TOUCH | 73.4% | 10.000xm | 41/67 (61.2%) | 39/42 (92.9%) | 0.174x | -0.059x | 0.303x | 23.9% |
| DEV | UPPER | SHORT | TF05 | S5_DETECTOR_EXTREME_CLOSE5 | 66.1% | 30.000xm | 33/67 (49.3%) | 39/42 (92.9%) | 0.115x | -0.065x | 0.240x | 31.2% |
| DEV | LOWER | LONG | TF60 | D0_WALL_TOUCH | 50.0% | 22.500xm | 16/49 (32.7%) | 22/27 (81.5%) | 0.042x | -0.041x | 0.024x | 43.4% |
| DEV | LOWER | LONG | TF60 | S1_WALL_CLOSE5 | 46.1% | 25.000xm | 14/49 (28.6%) | 21/27 (77.8%) | -0.011x | -0.053x | -0.001x | 46.1% |
| DEV | LOWER | LONG | TF60 | S2_WALL_ACCEPT2 | 42.1% | 60.000xm | 14/49 (28.6%) | 18/27 (66.7%) | -0.011x | -0.061x | -0.047x | 46.1% |
| DEV | LOWER | LONG | TF60 | S3_WALL_CLOSE15 | 40.8% | 60.000xm | 13/49 (26.5%) | 18/27 (66.7%) | 0.011x | -0.046x | -0.042x | 47.4% |
| DEV | LOWER | LONG | TF60 | S4_DETECTOR_EXTREME_TOUCH | 27.6% | 100.000xm | 6/49 (12.2%) | 15/27 (55.6%) | -0.142x | -0.052x | -0.138x | 56.6% |
| DEV | LOWER | LONG | TF60 | S5_DETECTOR_EXTREME_CLOSE5 | 22.4% | 85.000xm | 6/49 (12.2%) | 11/27 (40.7%) | -0.135x | -0.048x | -0.097x | 56.6% |
| REF | UPPER | SHORT | TF05 | D0_WALL_TOUCH | 75.5% | 5.000xm | 16/29 (55.2%) | 24/24 (100.0%) | 0.160x | -0.005x | 0.430x | 24.5% |
| REF | UPPER | SHORT | TF05 | S1_WALL_CLOSE5 | 62.3% | 10.000xm | 10/29 (34.5%) | 23/24 (95.8%) | 0.102x | 0.014x | 0.332x | 35.8% |
| REF | UPPER | SHORT | TF05 | S2_WALL_ACCEPT2 | 52.8% | 15.000xm | 6/29 (20.7%) | 22/24 (91.7%) | 0.090x | 0.028x | 0.276x | 43.4% |
| REF | UPPER | SHORT | TF05 | S3_WALL_CLOSE15 | 58.5% | 15.000xm | 8/29 (27.6%) | 23/24 (95.8%) | 0.089x | 0.028x | 0.283x | 39.6% |
| REF | UPPER | SHORT | TF05 | S4_DETECTOR_EXTREME_TOUCH | 69.8% | 5.000xm | 13/29 (44.8%) | 24/24 (100.0%) | 0.113x | -0.009x | 0.388x | 30.2% |
| REF | UPPER | SHORT | TF05 | S5_DETECTOR_EXTREME_CLOSE5 | 54.7% | 10.000xm | 8/29 (27.6%) | 21/24 (87.5%) | 0.073x | -0.005x | 0.269x | 39.6% |
| REF | LOWER | LONG | TF60 | D0_WALL_TOUCH | 59.5% | 30.000xm | 12/24 (50.0%) | 13/18 (72.2%) | 0.115x | -0.060x | 0.156x | 28.6% |
| REF | LOWER | LONG | TF60 | S1_WALL_CLOSE5 | 54.8% | 45.000xm | 10/24 (41.7%) | 13/18 (72.2%) | 0.000x | -0.074x | 0.176x | 33.3% |
| REF | LOWER | LONG | TF60 | S2_WALL_ACCEPT2 | 38.1% | 50.000xm | 5/24 (20.8%) | 11/18 (61.1%) | 0.016x | -0.017x | 0.158x | 45.2% |
| REF | LOWER | LONG | TF60 | S3_WALL_CLOSE15 | 42.9% | 45.000xm | 5/24 (20.8%) | 13/18 (72.2%) | -0.000x | -0.016x | 0.177x | 45.2% |
| REF | LOWER | LONG | TF60 | S4_DETECTOR_EXTREME_TOUCH | 31.0% | 55.000xm | 4/24 (16.7%) | 9/18 (50.0%) | 0.143x | -0.033x | 0.103x | 47.6% |
| REF | LOWER | LONG | TF60 | S5_DETECTOR_EXTREME_CLOSE5 | 28.6% | 60.000xm | 3/24 (12.5%) | 9/18 (50.0%) | 0.134x | -0.020x | 0.102x | 50.0% |
| ALL | UPPER | SHORT | TF05 | D0_WALL_TOUCH | 81.5% | 5.000xm | 67/96 (69.8%) | 65/66 (98.5%) | 0.175x | -0.052x | 0.416x | 17.9% |
| ALL | UPPER | SHORT | TF05 | S1_WALL_CLOSE5 | 69.8% | 15.000xm | 49/96 (51.0%) | 64/66 (97.0%) | 0.136x | -0.043x | 0.322x | 29.0% |
| ALL | UPPER | SHORT | TF05 | S2_WALL_ACCEPT2 | 59.9% | 30.000xm | 37/96 (38.5%) | 60/66 (90.9%) | 0.119x | -0.028x | 0.278x | 36.4% |
| ALL | UPPER | SHORT | TF05 | S3_WALL_CLOSE15 | 62.3% | 30.000xm | 38/96 (39.6%) | 63/66 (95.5%) | 0.105x | -0.025x | 0.269x | 35.8% |
| ALL | UPPER | SHORT | TF05 | S4_DETECTOR_EXTREME_TOUCH | 72.2% | 10.000xm | 54/96 (56.2%) | 63/66 (95.5%) | 0.143x | -0.043x | 0.334x | 25.9% |
| ALL | UPPER | SHORT | TF05 | S5_DETECTOR_EXTREME_CLOSE5 | 62.3% | 25.000xm | 41/96 (42.7%) | 60/66 (90.9%) | 0.112x | -0.045x | 0.267x | 34.0% |
| ALL | LOWER | LONG | TF60 | D0_WALL_TOUCH | 53.4% | 25.000xm | 28/73 (38.4%) | 35/45 (77.8%) | 0.065x | -0.048x | 0.100x | 38.1% |
| ALL | LOWER | LONG | TF60 | S1_WALL_CLOSE5 | 49.2% | 35.000xm | 24/73 (32.9%) | 34/45 (75.6%) | -0.000x | -0.060x | 0.086x | 41.5% |
| ALL | LOWER | LONG | TF60 | S2_WALL_ACCEPT2 | 40.7% | 57.500xm | 19/73 (26.0%) | 29/45 (64.4%) | -0.005x | -0.045x | 0.044x | 45.8% |
| ALL | LOWER | LONG | TF60 | S3_WALL_CLOSE15 | 41.5% | 60.000xm | 18/73 (24.7%) | 31/45 (68.9%) | 0.000x | -0.035x | 0.059x | 46.6% |
| ALL | LOWER | LONG | TF60 | S4_DETECTOR_EXTREME_TOUCH | 28.8% | 72.500xm | 10/73 (13.7%) | 24/45 (53.3%) | -0.071x | -0.045x | -0.038x | 53.4% |
| ALL | LOWER | LONG | TF60 | S5_DETECTOR_EXTREME_CLOSE5 | 24.6% | 75.000xm | 9/73 (12.3%) | 20/45 (44.4%) | -0.076x | -0.038x | -0.002x | 54.2% |

## DEV nomination -> REF holdout

| Side | Dir | TF | DEV nomination | DEV false-stop | DEV loser catch | DEV improve | DEV mean Δ | DEV q10 Δ | REF false-stop | REF loser catch | REF improve | REF mean Δ | REF q10 Δ | Validated |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| UPPER | SHORT | TF05 | NO_NOMINATION | — | — | — | — | — | — | — | — | — | — | NO |
| LOWER | LONG | TF60 | NO_NOMINATION | — | — | — | — | — | — | — | — | — | — | NO |

## Gate
- REF-validated SHORT invalidation: **NO**.
- REF-validated LONG invalidation: **NO**.
- Final S6 gate: **NOT READY FOR S7 — inspect failure anatomy before TP optimization**.

S6 does not optimize TP, trade WR, PF, expectancy, leverage, or PnL.
