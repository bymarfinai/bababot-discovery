# BTC Temporal Saturday T-Method S5.1A — Adaptive Failure Timing/Persistence Atlas

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — ADAPTIVE FAILURE PERSISTENCE IS REAL; NO ACTION RULE PROMOTED YET  
**Research only:** live BBC untouched  
**Frozen references preserved:** parent +$87.20; A7.19 +$103.383; A7.26 remains the selective candidate.

## Method

The frozen Saturday FAILURE signature was evaluated every completed 5m decision from +15m through +180m while the original position remained alive:

`decision-open progress <= -0.10% AND cumulative taker edge < 0`

No FAILURE threshold was changed. No CUT/FLIP action was applied.

The atlas mapped:
- first failure onset
- consecutive failure persistence
- recovery to the frozen sign-symmetric HEALTHY state
- EMA20 reclaim after failure
- pre-entry PULLBACK / NORMAL / STRETCHED context
- whether +0.5 or +0.8 impulse was eventually established
- parent and A7.19 economics

Persistence cuts 5/10/15/20/30m are descriptive atlas views, not a promoted rule selection.

## Frozen parity

- Parent: 139 occurrences / 65W / 74L / PnL +$87.20
- A7.19: PnL +$103.383
- Exact frozen +60m FAILURE parity preserved: 30 signals = 17 discovery / 13 validation

## 1. Any FAILURE between +15m and +180m

### ANY_FAILURE
- N77 = 49 discovery / 28 validation
- A7.19 loss rate 63.64%
- A7.19 cohort PnL **-$71.698**
- discovery loss 59.18% / -$33.058
- validation loss 71.43% / -$38.640
- eventual deep-runner rate 32.47%

### NO_FAILURE_15_180
- N62 = 34 / 28
- A7.19 loss rate only 32.26%
- A7.19 cohort PnL **+$175.081**
- discovery loss 29.41% / +$99.646
- validation loss 35.71% / +$75.435
- eventual deep-runner rate 58.06%

Thus a causal failure episode is meaningful, but a single episode is not sufficient as an exit trigger.

## 2. First failure onset timing

| First onset | N D/V | A7.19 loss | A7.19 PnL | Discovery | Validation | Deep runner |
|---|---:|---:|---:|---:|---:|---:|
| 15–30m | 35 22/13 | 57.14% | +$3.762 | 45.45% / +$19.000 | 76.92% / -$15.239 | 40.00% |
| 35–60m | 19 11/8 | **73.68%** | **-$31.061** | 72.73% / -$19.577 | 75.00% / -$11.484 | 21.05% |
| 65–120m | 8 6/2 | 75.00% | -$22.567 | 83.33% / -$22.335 | 50.00% / -$0.232 | 25.00% |
| 125–180m | 15 10/5 | 60.00% | -$21.831 | 60.00% / -$10.146 | 60.00% / -$11.685 | 33.33% |

Key interpretation:
- very early 15–30m failure is regime-sensitive and should not be acted on blindly
- first failure emerging around 35–60m is much more consistently bad across discovery and validation
- there is no evidence that one fixed clock checkpoint is universally optimal

## 3. Failure persistence atlas

| Persistence achieved | N D/V | A7.19 loss | A7.19 PnL | Discovery loss | Validation loss |
|---|---:|---:|---:|---:|---:|
| >=5m | 77 49/28 | 63.64% | -$71.698 | 59.18% | 71.43% |
| >=10m | 69 44/25 | **65.22%** | **-$78.439** | **61.36%** | **72.00%** |
| >=15m | 61 38/23 | 63.93% | -$65.921 | 57.89% | 73.91% |
| >=20m | 54 33/21 | 62.96% | -$52.371 | 57.58% | 71.43% |
| >=30m | 41 23/18 | **65.85%** | **-$32.367** | **60.87%** | **72.22%** |

Natural result:
- persistence does matter
- >=10m is the earliest persistence cut with adequate support in both halves and >60% A7.19 loss rate in both halves
- >=30m remains similarly bad but catches fewer occurrences
- the relationship is not monotonic enough to justify threshold optimization on this same sample

Therefore S5.1A does **not** select 10m or 30m as a rule; it establishes that persistence is more useful than a single fixed +60m snapshot.

## 4. Pre-entry state x 15m persistence

### PULLBACK + PERSIST15
- N23 = 19 / 4
- A7.19 loss 52.17%
- PnL -$4.002
- discovery loss only 42.11% / +$10.708
- validation 100% loss / -$14.710
- deep-runner rate 43.48%

Too imbalanced chronologically. This confirms that pullback-born Saturday trades require caution before early intervention.

### NORMAL + PERSIST15
- N30 = 16 / 14
- A7.19 loss 66.67%
- PnL -$47.878
- discovery loss 75.00%
- validation loss 57.14%

Bad aggregate but validation falls below the predeclared stable-bad standard.

### STRETCHED + PERSIST15
- N8 = 3 / 5
- A7.19 loss **87.50%**
- PnL -$14.042
- discovery 66.67% loss
- validation 100% loss
- deep-runner rate **0%**

Mechanistically very strong, but discovery N3 is too small for promotion.

Preserve only as a shadow clue.

## 5. Recovery after first FAILURE

The frozen sign-symmetric HEALTHY state was strict:

`progress >= +0.10% AND cumulative taker edge > 0`

Only 7 failure trades recovered to HEALTHY within 60m, and all seven were in discovery. Therefore direct HEALTHY recovery timing is not chronologically transferable enough to use as the adaptive reset definition.

More useful is the absence of recovery:

### FAILURE + NO HEALTHY within 60m
- N70 = 42 / 28
- A7.19 loss **65.71%**
- A7.19 PnL **-$75.232**
- discovery loss **61.90%**
- validation loss **71.43%**
- deep-runner rate 28.57%

This is a stable descriptive BAD state, but because HEALTHY recovery itself is absent in validation, it is not yet the preferred action trigger.

## 6. EMA20 reclaim after first FAILURE

### Reclaim within 30m
- N12 = 7 / 5
- aggregate loss 50%
- discovery loss 28.57%
- validation loss 80%

Reclaim itself is not a stable GOOD reset.

### No EMA20 reclaim within 60m
- N59 = 38 / 21
- A7.19 loss **66.10%**
- A7.19 PnL **-$69.114**
- discovery loss **63.16%**
- validation loss **71.43%**
- deep-runner rate 32.20%

This is the cleanest adaptive failure-to-recover state because it has adequate support and the same harmful direction in both chronological halves.

## 7. Composite diagnostics

### PERSIST15 + NO_HEALTHY60
- N59 = 36 / 23
- loss 64.41%
- discovery 58.33%
- validation 73.91%

Discovery misses the stable-bad threshold.

### PERSIST20 + NO_HEALTHY60
- N54 = 33 / 21
- loss 62.96%
- discovery 57.58%
- validation 71.43%

Same issue.

### PERSIST15 + NO03 at first failure
- N54 = 33 / 21
- loss 64.81%
- discovery 57.58%
- validation 76.19%

Again validation stronger than discovery; not promoted.

## 8. Stable descriptive candidates

Using the predeclared support requirement of at least 5 occurrences in both chronological halves and same directional outcome:

1. `PERSIST_10M`
   - N69 = 44 / 25
   - loss 65.22%
   - discovery 61.36%
   - validation 72.00%

2. `PERSIST_30M`
   - N41 = 23 / 18
   - loss 65.85%
   - discovery 60.87%
   - validation 72.22%

3. `FAIL_NO_HEALTHY<=60M`
   - N70 = 42 / 28
   - loss 65.71%
   - discovery 61.90%
   - validation 71.43%

4. `FAIL_NO_EMA_RECLAIM<=60M`
   - N59 = 38 / 21
   - loss **66.10%**
   - discovery **63.16%**
   - validation **71.43%**

## S5.1A verdict

**PASS: adaptive failure timing/persistence is real.**

The correct Saturday interpretation is not:

`wait exactly 60m -> evaluate FAILURE`

It is closer to:

`observe every completed 5m -> detect FAILURE episode -> measure whether failure persists / whether structure can recover`

A single early warning is too noisy, especially at 15–30m. Persistence and failure-to-recover provide materially stronger causal information.

The cleanest next research candidate is **not** a retuned clock boundary. It is the already-frozen FAILURE condition followed by **no causal EMA20 reclaim for up to 60m after the first failure episode**. This state has adequate discovery/validation support and stable harmful economics.

However no management action is promoted yet. The next step, if continuing the early-failure branch, should be **one tightly predeclared S5.1B action test** on the frozen `FAIL -> NO EMA20 RECLAIM within 60m` state. Do not sweep action timing or thresholds. If that direct economic action still fails, close the early-failure branch and proceed to S5.2 selective RUNNER vs PROTECT.
