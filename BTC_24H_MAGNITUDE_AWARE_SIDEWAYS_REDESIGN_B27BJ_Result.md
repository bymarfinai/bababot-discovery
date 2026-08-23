# B27BJ — BTC 24H Magnitude-Aware SIDEWAYS Redesign Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Detector redesign only; no LONG/SHORT mapping, entry, stop, target, fee, WR, PF, PnL, or session optimization was used.

B27BI identity reproduced exactly: **1,023 episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.**

## Frozen model

Separate BULL-origin and BEAR-origin L2 logistic regressions were fit on **development only**, using the six preregistered B27BI continuous causal features. External and reference_validation were not used for scaling, fitting, thresholding, feature selection, or model choice. Threshold was frozen at `P(RESUME)>=0.50`.

## Classifier metrics

| Origin | Partition | N | Actual resume | Pred resume | AUC | Balanced acc | Resume recall | Transition recall | Brier |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BULL | development | 219 | 47.9% | 53.9% | 0.729 | 0.678 | 72.4% | 63.2% | 0.205 |
| BULL | external | 163 | 63.8% | 51.5% | 0.652 | 0.612 | 59.6% | 62.7% | 0.253 |
| BULL | reference_validation | 150 | 48.0% | 61.3% | 0.763 | 0.685 | 80.6% | 56.4% | 0.206 |
| BULL | POOLED_OOS | 313 | 56.2% | 56.2% | 0.690 | 0.637 | 68.2% | 59.1% | 0.230 |
| BULL | august | 0 | - | - | - | - | - | - | - |
| BEAR | development | 249 | 54.2% | 63.1% | 0.750 | 0.693 | 80.7% | 57.9% | 0.195 |
| BEAR | external | 108 | 51.9% | 66.7% | 0.664 | 0.587 | 75.0% | 42.3% | 0.237 |
| BEAR | reference_validation | 134 | 41.0% | 60.4% | 0.637 | 0.558 | 67.3% | 44.3% | 0.255 |
| BEAR | POOLED_OOS | 242 | 45.9% | 63.2% | 0.654 | 0.573 | 71.2% | 43.5% | 0.247 |
| BEAR | august | 0 | - | - | - | - | - | - | - |

## OOS confusion accounting

| Origin | OOS N | RESUME->RESUME | RESUME->TRANSITION | TRANSITION->RESUME (4h delayed SIDEWAYS) | TRANSITION->TRANSITION |
|---|---:|---:|---:|---:|---:|
| BULL | 313 | 120 | 56 | 56 | 81 |
| BEAR | 242 | 79 | 32 | 74 | 57 |

## Raw vs redesigned detector

- Raw pooled-major one-interval flip-back: **459/2202 = 20.8%**.
- B27BJ pooled-major one-interval flip-back: **177/1640 = 10.8%**.
- First-SIDEWAYS intervals tagged `INHERITED_PAUSE`: **604**.
- Raw maximum major-partition occupancy drift: **20.5pp**.
- B27BJ maximum major-partition occupancy drift: **21.2pp**.
- Raw direct BULL<->BEAR change share: **7.0%**.
- B27BJ direct BULL<->BEAR change share: **13.5%**.

### BULL / BEAR persistence by partition

| Partition | State | Raw persistence | B27BJ persistence | Raw occupancy | B27BJ occupancy |
|---|---|---:|---:|---:|---:|
| external | BULL | 92.6% | 94.3% | 51.6% | 53.5% |
| external | BEAR | 88.2% | 90.9% | 23.0% | 24.6% |
| development | BULL | 90.9% | 93.1% | 44.8% | 46.5% |
| development | BEAR | 89.6% | 92.4% | 43.4% | 45.8% |
| reference_validation | BULL | 88.5% | 91.8% | 43.0% | 45.7% |
| reference_validation | BEAR | 89.4% | 91.6% | 42.0% | 44.4% |
| POOLED_MAJOR | BULL | 90.9% | 93.2% | 46.4% | 48.5% |
| POOLED_MAJOR | BEAR | 89.3% | 91.9% | 36.9% | 39.0% |

## Frozen promotion gate

- Identity / causality: **PASS**.
- AUC >=0.60 in external AND validation for each origin: **PASS**.
- Pooled-OOS balanced accuracy >=0.57 for each origin: **PASS**.
- Pooled-OOS TRANSITION recall >=0.55 for each origin: **FAIL**.
- Flip-back improves and <=18.0%: **PASS**.
- BULL/BEAR persistence >=60% in every major partition: **PASS**.
- Occupancy drift does not worsen vs raw: **FAIL**.

**Frozen verdict: `B27BJ_MAGNITUDE_AWARE_REDESIGN_NOT_SUPPORTED`.**

## Interpretation boundary

If supported, B27BJ only supports this exact one-bar magnitude-aware inherited-pause redesign as a regime detector candidate. It does not establish any trading direction or entry rule. If not supported, no B27BJ threshold/model/state semantics may be modified post hoc; a new experiment ID is required.

Research only. Live BBC unchanged.
