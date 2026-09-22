# BNB B40-S13 — Post-T1 Failure Persistence / Rescue Confirmation

XP1 signature: 3694b8e4ccfc089d7b65082b0acb784f0e77fdb873998542ee8ce12dfe69c3e8
S13 signature: 35ecc7af764dce2f0fa42a1c04b9b8da37f6eaafb56988ce7603282cf586f13b

S13 keeps T0.5 / ANCHOR only and asks whether persistence or failed reclaim makes the S12 warning executable.

## Persistence / rescue audit

| Period | Target | Candidate | Signal | Cat captured | Winner false-exit | Precision | Med exit R | Med R improve | Lead to cat | Later target after false exit | CF Exp | Δ vs T1 | Δ vs unprotected | PF | MaxDD |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | T15 | P1_ANCHOR_TWO_CONSEC_CLOSE5 | 15/71 (21.1%) | 10/10 (100.0%) | 4/59 (6.8%) | 73.3% | -0.337R | 0.661R | 112.5m | 4/4 (100.0%) | 0.009R | 0.024R | 0.012R | 1.020 | 23.436R |
| DEV | T15 | P2_ANCHOR_THREE_CONSEC_CLOSE5 | 15/71 (21.1%) | 10/10 (100.0%) | 4/59 (6.8%) | 73.3% | -0.272R | 0.814R | 100.0m | 4/4 (100.0%) | 0.010R | 0.025R | 0.013R | 1.023 | 23.774R |
| DEV | T15 | P3_T05_THEN_ANCHOR_CLOSE5 | 15/71 (21.1%) | 10/10 (100.0%) | 4/59 (6.8%) | 73.3% | -0.215R | 0.887R | 117.5m | 4/4 (100.0%) | 0.013R | 0.028R | 0.015R | 1.028 | 23.003R |
| DEV | T15 | P4_ANCHOR_RECLAIM_REJECT5 | 10/71 (14.1%) | 6/10 (60.0%) | 3/59 (5.1%) | 70.0% | -0.279R | 0.725R | 167.5m | 3/3 (100.0%) | 0.003R | 0.018R | 0.006R | 1.007 | 24.404R |
| DEV | T2 | P1_ANCHOR_TWO_CONSEC_CLOSE5 | 26/71 (36.6%) | 16/16 (100.0%) | 6/45 (13.3%) | 76.9% | -0.361R | 0.483R | 72.5m | 6/6 (100.0%) | -0.027R | -0.012R | 0.002R | 0.945 | 27.429R |
| DEV | T2 | P2_ANCHOR_THREE_CONSEC_CLOSE5 | 25/71 (35.2%) | 15/16 (93.8%) | 6/45 (13.3%) | 76.0% | -0.323R | 0.703R | 95.0m | 6/6 (100.0%) | -0.026R | -0.011R | 0.003R | 0.946 | 27.453R |
| DEV | T2 | P3_T05_THEN_ANCHOR_CLOSE5 | 26/71 (36.6%) | 16/16 (100.0%) | 6/45 (13.3%) | 76.9% | -0.261R | 0.556R | 117.5m | 6/6 (100.0%) | -0.020R | -0.005R | 0.009R | 0.958 | 27.478R |
| DEV | T2 | P4_ANCHOR_RECLAIM_REJECT5 | 19/71 (26.8%) | 10/16 (62.5%) | 5/45 (11.1%) | 73.7% | -0.282R | 0.661R | 167.5m | 5/5 (100.0%) | -0.029R | -0.014R | -0.000R | 0.941 | 28.047R |
| REF | T15 | P1_ANCHOR_TWO_CONSEC_CLOSE5 | 15/46 (32.6%) | 8/10 (80.0%) | 6/35 (17.1%) | 60.0% | -0.294R | 0.176R | 50.0m | 6/6 (100.0%) | 0.081R | -0.053R | -0.023R | 1.207 | 12.810R |
| REF | T15 | P2_ANCHOR_THREE_CONSEC_CLOSE5 | 15/46 (32.6%) | 8/10 (80.0%) | 6/35 (17.1%) | 60.0% | -0.331R | 0.206R | 45.0m | 6/6 (100.0%) | 0.083R | -0.051R | -0.021R | 1.213 | 12.406R |
| REF | T15 | P3_T05_THEN_ANCHOR_CLOSE5 | 19/46 (41.3%) | 10/10 (100.0%) | 8/35 (22.9%) | 57.9% | -0.240R | 0.385R | 35.0m | 8/8 (100.0%) | 0.089R | -0.046R | -0.015R | 1.238 | 12.064R |
| REF | T15 | P4_ANCHOR_RECLAIM_REJECT5 | 8/46 (17.4%) | 3/10 (30.0%) | 4/35 (11.4%) | 50.0% | -0.172R | -0.699R | 35.0m | 4/4 (100.0%) | 0.086R | -0.048R | -0.018R | 1.215 | 10.130R |
| REF | T2 | P1_ANCHOR_TWO_CONSEC_CLOSE5 | 18/46 (39.1%) | 11/13 (84.6%) | 4/30 (13.3%) | 77.8% | -0.343R | 0.460R | 65.0m | 4/4 (100.0%) | 0.124R | -0.011R | 0.004R | 1.310 | 11.519R |
| REF | T2 | P2_ANCHOR_THREE_CONSEC_CLOSE5 | 18/46 (39.1%) | 11/13 (84.6%) | 4/30 (13.3%) | 77.8% | -0.375R | 0.660R | 60.0m | 4/4 (100.0%) | 0.121R | -0.013R | 0.001R | 1.301 | 11.167R |
| REF | T2 | P3_T05_THEN_ANCHOR_CLOSE5 | 21/46 (45.7%) | 13/13 (100.0%) | 5/30 (16.7%) | 76.2% | -0.284R | 0.687R | 40.0m | 5/5 (100.0%) | 0.137R | 0.003R | 0.017R | 1.362 | 10.389R |
| REF | T2 | P4_ANCHOR_RECLAIM_REJECT5 | 11/46 (23.9%) | 5/13 (38.5%) | 4/30 (13.3%) | 63.6% | -0.253R | -0.253R | 95.0m | 4/4 (100.0%) | 0.106R | -0.028R | -0.014R | 1.255 | 11.304R |

## Advance-rule audit

| Target | Candidate | DEV Δbase | REF Δbase | DEV cat | REF cat | DEV false | REF false | Annual >=0 | PASS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| T15 | P1_ANCHOR_TWO_CONSEC_CLOSE5 | 0.012R | -0.023R | 100.0% | 80.0% | 6.8% | 17.1% | 2/5 | NO |
| T15 | P2_ANCHOR_THREE_CONSEC_CLOSE5 | 0.013R | -0.021R | 100.0% | 80.0% | 6.8% | 17.1% | 2/5 | NO |
| T15 | P3_T05_THEN_ANCHOR_CLOSE5 | 0.015R | -0.015R | 100.0% | 100.0% | 6.8% | 22.9% | 3/5 | NO |
| T15 | P4_ANCHOR_RECLAIM_REJECT5 | 0.006R | -0.018R | 60.0% | 30.0% | 5.1% | 11.4% | 3/5 | NO |
| T2 | P1_ANCHOR_TWO_CONSEC_CLOSE5 | 0.002R | 0.004R | 100.0% | 84.6% | 13.3% | 13.3% | 3/5 | NO |
| T2 | P2_ANCHOR_THREE_CONSEC_CLOSE5 | 0.003R | 0.001R | 93.8% | 84.6% | 13.3% | 13.3% | 3/5 | NO |
| T2 | P3_T05_THEN_ANCHOR_CLOSE5 | 0.009R | 0.017R | 100.0% | 100.0% | 13.3% | 16.7% | 4/5 | NO |
| T2 | P4_ANCHOR_RECLAIM_REJECT5 | -0.000R | -0.014R | 62.5% | 38.5% | 11.1% | 13.3% | 2/5 | NO |

## Interpretation boundary
S13 changes only post-warning confirmation semantics; entry, structural failure, XP1, T1 milestone and farther targets remain frozen.
A target traded intrabar always has priority over a close-based failure confirmation on the same 5m bar.
No candidate is promoted unless the preregistered cross-period and annual advance rule is passed.
