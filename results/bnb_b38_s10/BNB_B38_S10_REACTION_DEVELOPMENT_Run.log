# BNB B38-S10 — Reaction Development Entry State Machine

**Reclaim is now a state, not automatically an entry.**

## Results

| Period | Candidate | Entries | Invalidated pre-entry | No state | W-L | WR | Exp | PF | Baseline WINs entered | Baseline WINs still WIN | Baseline LOSS avoided | Genuine zone-fail avoided |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | E1_RECLAIM_HIGH_BREAK | 469 | 312 | 0 | 329-140 | 70.1% | 0.072R | 1.240 | 324/353 (91.8%) | 290/353 (82.2%) | 185 | 137 |
| DEV | E2_RECLAIM_HOLD_THEN_BREAK | 440 | 337 | 0 | 325-115 | 73.9% | 0.035R | 1.133 | 313/353 (88.7%) | 283/353 (80.2%) | 200 | 144 |
| DEV | E3_PROTECTED_LOW_THEN_BREAK | 394 | 381 | 0 | 307-87 | 77.9% | -0.001R | 0.994 | 290/353 (82.2%) | 253/353 (71.7%) | 221 | 153 |
| REF | E1_RECLAIM_HIGH_BREAK | 294 | 164 | 0 | 203-91 | 69.0% | 0.015R | 1.048 | 200/212 (94.3%) | 179/212 (84.4%) | 95 | 78 |
| REF | E2_RECLAIM_HOLD_THEN_BREAK | 272 | 184 | 0 | 201-71 | 73.9% | -0.002R | 0.993 | 192/212 (90.6%) | 176/212 (83.0%) | 109 | 86 |
| REF | E3_PROTECTED_LOW_THEN_BREAK | 249 | 207 | 0 | 189-60 | 75.9% | -0.074R | 0.695 | 184/212 (86.8%) | 159/212 (75.0%) | 123 | 91 |

## Interpretation boundary
Invalidated-before-entry events are avoided trades, not converted wins.
The key preservation metric is how many historical baseline WIN events still progress to an entry and remain WIN under the later state-machine geometry.
No S10 candidate is promoted automatically.
