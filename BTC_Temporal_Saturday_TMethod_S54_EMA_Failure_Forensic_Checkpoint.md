# BTC Temporal Saturday T-Method S5.4 — EMA Failure-State Forensic

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — FORENSIC PASS; NO EMA ACTION PROMOTED  
**Research only:** live BBC untouched

## Frozen parity
- Saturday +0.50 hinge trades: **89**
- Future deep >=+0.80: **61**
- Shallow +0.50..<+0.80: **28**
- Static parent all-trade PnL: **+$87.200**
- A7.19 full-coverage PnL: **+$103.383**

## Main finding
Saturday does have a causal EMA relationship after the +0.50 favorable hinge, but it is **not the Tuesday overextension pattern**.

At the completed +0.50 hinge, future deep runners are generally **more extended above EMA7/EMA20 and have stronger positive short-term EMA slope** than shallow runners. This direction is stable in discovery and validation.

### Hinge close distance to EMA7
- Deep median: **+0.1855%**
- Shallow median: **+0.1676%**
- Full AUC: **0.597**
- Discovery AUC: **0.618**, DEEP_HIGH
- Validation AUC: **0.594**, DEEP_HIGH

### Hinge close distance to EMA20
- Deep median: **+0.2942%**
- Shallow median: **+0.2860%**
- Full AUC: **0.590**
- Discovery AUC: **0.586**, DEEP_HIGH
- Validation AUC: **0.583**, DEEP_HIGH

### EMA7 5m slope
- Deep median: **+0.0619% / 5m**
- Shallow median: **+0.0559% / 5m**
- Discovery / validation AUC: **0.618 / 0.594**, same DEEP_HIGH direction.

### EMA20 5m slope
- Deep median: **+0.0310% / 5m**
- Shallow median: **+0.0301% / 5m**
- Discovery / validation AUC: **0.586 / 0.583**, same DEEP_HIGH direction.

### EMA7 60m slope
- Deep median: **+0.2165% / 60m**
- Shallow median: **+0.1874% / 60m**
- Discovery / validation AUC: **0.549 / 0.634**, same DEEP_HIGH direction.

The strongest non-EMA hinge separator remains actual hinge close progress:
- Deep median: **+0.5023%**
- Shallow median: **+0.4688%**
- Full AUC **0.666**
- Discovery / validation AUC **0.604 / 0.732**.

Pre-hinge MAE is also directionally consistent: deep runners have lower adverse excursion than shallow runners, though separation is modest.

## Hinge reclaim hypothesis is not useful
At +0.50 hinge:
- 88/89 trades close above EMA7.
- 89/89 close above EMA20.
- EMA7 reclaim at the hinge occurs only 2 times.
- EMA20 reclaim at the hinge occurs 0 times.

Therefore hinge-time `above EMA` / `reclaim` is effectively saturated and cannot route Saturday trades.

This is analogous to Tuesday A5.4's lesson that the obvious hinge-reclaim idea is causally mistimed, but the direction differs: Saturday deep runners look **stronger**, not more exhausted, at the hinge.

## Post-hinge EMA failure timing
A simple eventual EMA break is also too broad: almost all deep and shallow runners eventually close below EMA7/EMA20 before their frozen exit.

The more informative feature is **how quickly acceptance below EMA occurs after the +0.50 hinge**.

### First completed close below EMA20
- Deep median: **60m** after hinge
- Shallow median: **40m**
- Discovery: **60m vs 40m**
- Validation: **72.5m vs 40m**

### Two consecutive completed closes below EMA7
- Deep median: **45m**
- Shallow median: **35m**
- Discovery: **40m vs 30m**
- Validation: **50m vs 40m**

### Two consecutive completed closes below EMA20
- Deep median: **85m**
- Shallow median: **60m**
- Discovery: **75m vs 55m**
- Validation: **105m vs 65m**

This timing direction is notably consistent: **shallow runners lose EMA structure sooner**, while latent deep runners often tolerate later EMA breaks and still recover.

### Negative control
The event *ever* occurring is not enough:
- first close below EMA7: deep 98.4%, shallow 92.9%
- first close below EMA20: deep 91.8%, shallow 89.3%
- two closes below EMA7: deep 96.7%, shallow 89.3%
- two closes below EMA20: deep 91.8%, shallow 85.7%

Thus `below EMA => exit` would almost certainly clip many valid Saturday runners, consistent with prior S5.2 findings.

## S5.4 verdict
**PASS as forensic evidence that EMA contains Saturday-native failure-state information.**

However the useful relationship is specific:
1. At +0.50, stronger future runners are slightly **more positively extended above EMA** and have stronger EMA momentum.
2. Hinge reclaim/above-EMA state is saturated and not useful.
3. A later EMA break is common even for deep runners, so global EMA exits are not justified.
4. **Earlier post-hinge loss/acceptance below EMA7/EMA20** is the cleaner failure clue, with the timing direction preserved in discovery and validation.

## Correct continuation
Proceed to **S5.5**, but do **not** copy Tuesday's `more overextended = failure` assumption.

Saturday-native S5.5 should test a small causal family around **EMA impulse quality + early post-hinge loss of EMA structure**, while preserving late/normal EMA pullbacks. No global EMA exit and no timing threshold sweep.

A7.19 remains the official full-coverage Saturday champion; A7.26 remains the preserved selective benchmark.
