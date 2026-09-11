# START HERE — Pair-Native Character Discovery Playbook

**Purpose:** canonical handoff for discovering the native trading character of a new pair before real-execution optimization.

**Critical rule:** transfer the **research process**, never the discovered character of another pair. BTC, ETH, SOL, BNB, or any future pair may require different hours, state families, lookbacks, payoff horizons, and eventually different execution logic. A successful ETH coordinate is evidence about ETH only.

**Research status:** Development/shadow research only. This document does not authorize live deployment. OOS/holdout data must remain closed during character discovery unless a separate preregistered validation experiment explicitly opens it.

---

## 1. Research objective

For every new pair, answer these questions in order:

1. **Does the pair have a reproducible LONG character at particular times of day?**
2. **Which causal pre-entry state describes that character?**
3. **What lookback and payoff horizon are native to that hour/pair?**
4. **Is the effect broad across the four quarter-hour anchors inside the hour?**
5. **Is the effect economically acceptable when opportunities are pooled chronologically?**
6. **Does it survive multiple Development eras?**
7. Only after the full temporal character map exists: **how should a one-position live executor select and close actual trades?**
8. Only after LONG execution semantics are understood should SHORT be added, unless a separate preregistered research program explicitly chooses the opposite order.

This separation is mandatory. **Character discovery is not execution discovery.**

---

## 2. What is transferable vs. what is not

### Transfer to every pair

- causal/no-look-ahead research discipline;
- Development-only selection;
- preregistration before seeing results;
- one-hour-at-a-time sweep;
- four quarter-hour anchors per hour;
- the initial causal state grammar;
- frozen economic/robustness gates;
- persistence of every experiment and verdict;
- failure taxonomy;
- completion of the full 24-hour map before real-execution discovery;
- rule that a near-miss may guide a future experiment but may not be promoted retroactively.

### Do **not** transfer from another pair

- winning hour;
- winning quarter-hour;
- LONG/SHORT preference;
- winning state family;
- lookback;
- hold/payoff horizon;
- entry coordinate;
- TP/SL;
- session range;
- one-position selection rule;
- assumptions such as “high efficiency is bullish” or “H720 is best.”

Example: ETH finding `EFF_HIGH__RV_LOW / LB240 / H960` at one hour does **not** authorize testing that coordinate first on another pair. The new pair must earn its own character through the same search process.

---

## 3. Frozen data discipline

Before the first result is seen:

- define the pair and source data;
- use causal completed bars only;
- document timezone conversion explicitly;
- record raw-data coverage and require at least **99.5%** coverage for the intended Development window;
- freeze fees/notional assumptions used for comparative economics;
- define Development eras before searching;
- keep all OOS/reference-validation partitions unopened during discovery;
- never repair missing data, alter gates, or alter chronology after seeing the result without starting a new preregistered experiment ID.

The exact historical years can differ when data availability requires it, but the era partition must be frozen **before** candidate results are inspected.

---

## 4. Initial pair-agnostic LONG grammar

The first sweep is deliberately broad and causal. It searches state families rather than copying any known pair setup.

Core state dimensions include:

- prior drive direction: `DRIVE_UP`, `DRIVE_DOWN`;
- causal drive-strength percentile bands;
- path efficiency `EFF_LOW/MID/HIGH`;
- realized volatility `RV_LOW/MID/HIGH`;
- normalized path range `RANGE_LOW/MID/HIGH`;
- extension `EXT_LOW/MID/HIGH`;
- preregistered combinations of those dimensions;
- an `ALL` baseline where applicable.

For efficiency:

`eff = abs(path[-1] - path[0]) / sum(abs(diff(path)))`

This is **absolute path efficiency**, not bullish momentum. Direction must come from the separate drive/sign context when direction is required.

Percentile states must be causal: use only information available before the candidate entry. The E12 reference implementation used rolling prior observations with a minimum-history requirement; never let the current/future observation leak into its own percentile threshold.

The reference E12 grammar contained **90 causal rules**. Reusing that grammar is allowed as the common search language; reusing a pair's winning coordinate is not.

---

## 5. Frozen initial coordinate grid

For the first pair-native hourly sweep, use the common exploratory grid unless a new alternative grid is preregistered before seeing the pair's results:

- `LOOKBACKS = (15, 30, 60, 120, 240, 360)` minutes
- `HOLDS = (60, 120, 240, 360, 720, 960)` minutes
- 90 rules × 6 lookbacks × 6 holds = **3,240 candidates per hour**

Each hour contains four fixed anchors:

- `HH:00`
- `HH:15`
- `HH:30`
- `HH:45`

Search **one hour only per experiment**. Do not mix neighboring hours into the same candidate-search experiment.

The hold grid at this stage is a **payoff-horizon probe**, not the final live exit rule.

---

## 6. Frozen gates

### 6.1 Per-anchor supportive gate

An anchor is supportive only when all are true:

- trades `>= 40`
- WR `>= 52%`
- net PnL `> 0`
- expectancy `> 0`
- PF `>= 1.05`
- DD `<= $125` under the frozen reference economics
- max loss streak `<= 10`

### 6.2 Hour-level anchor gate

- evaluable anchors `>= 3`
- supportive anchors `>= 3`

### 6.3 Pooled economic gate

Across all qualifying quarter-hour opportunities in the tested hour:

- trades `>= 160`
- WR `>= 55%`
- net PnL `> 0`
- expectancy `>= +$0.50/trade`
- PF `>= 1.20`
- DD `<= $125`
- max loss streak `<= 8`

### 6.4 Development-era gate

For **each** frozen Development era:

- trades `>= 40`
- WR `>= 52%`
- net PnL `> 0`
- expectancy `> 0`
- PF `>= 1.05`

Additionally, at least **2 Development eras** must have WR `>= 55%`.

### 6.5 Formal candidate gate

`candidate_gate = anchor_gate AND pooled_gate AND era_gate`

A candidate is a formal PASS only when all three pass. High PnL, high WR, or high PF cannot override a failed formal gate.

---

## 7. Formal selection ranking

When one hour has multiple full-gate passers, rank **only the formal passers**. The reference ranking is:

1. higher minimum-era expectancy (`min_year_exp`);
2. more supportive anchors;
3. higher pooled expectancy;
4. higher pooled WR;
5. higher PF;
6. lower DD;
7. lower max loss streak;
8. lower hold;
9. lower lookback;
10. stable rule-name tie-break.

Never replace a formal passer with a prettier non-passer after inspecting the results.

---

## 8. Mandatory 24-hour sweep

**Learned improvement from the ETH program:** do not stop permanently after the first PASS.

Complete all **24 one-hour habitats** with the exact same frozen grammar and gates. This produces the pair's temporal fingerprint:

- formal PASS hours;
- no-pass zones;
- near-miss zones;
- state-family rotations;
- payoff-horizon rotations;
- quarter-hour toxicity/support patterns;
- era-dependent weaknesses;
- chronological/path-risk problems.

A PASS is a local result. The **full 24-hour map** is the pair character.

For every hour, persist at minimum:

- experiment ID and exact WIB/UTC range;
- branch/commit/run/job/artifact identity;
- raw coverage;
- count of 3,240 full passers;
- selected formal winner if any;
- strongest scientifically relevant near-miss if none;
- N, WR, net, expectancy, PF, DD, max loss streak, max win streak;
- anchor-by-anchor statistics;
- era-by-era statistics;
- anchor/pooled/era gate outcome;
- explicit failure mechanism;
- comparison to neighboring-hour families when informative.

---

## 9. How to interpret FAIL correctly

`FAIL` does **not** mean “unprofitable.” It means the candidate is not yet robust enough under the frozen character definition.

Classify failures instead of discarding them:

### A. No economic edge
Low/negative WR, expectancy, PF, or PnL. Usually low priority.

### B. Anchor-local edge
Good pooled economics but too few supportive quarter-hour anchors. The state may belong to a narrower clock habitat.

### C. Pooled path-risk failure
Strong WR/PF/expectancy and broad anchors, but DD or loss streak exceeds the gate. This is highly relevant later for **sequential one-position execution discovery**.

### D. Era-instability failure
Good pooled/anchor result but one Development era breaks. Do not rescue it; preserve it as a regime clue.

### E. Sample weakness
Attractive WR/PF from tiny N or non-evaluable anchors. Treat as descriptive only.

### F. Mixed failure
Several dimensions fail simultaneously. Lower priority unless a later independent experiment provides a reason to revisit it.

Near-misses are **future hypotheses**, never retroactive PASSes.

---

## 10. Scientific integrity / stop rules

During the 24-hour character sweep:

- no gate relaxation after seeing a result;
- no hand-picking a different candidate because PnL looks larger;
- no post-result coordinate rescue;
- no OOS opening;
- no TP/SL optimization;
- no SHORT mixed into a LONG experiment;
- no one-position selector mixed into the opportunity-character experiment;
- no changing fee/notional/chronology between hours;
- no claiming live readiness.

If a failure suggests a new idea, write a **new preregistration** and a new experiment ID.

---

## 11. Transition to real-execution discovery

Character discovery and live execution answer different questions.

The hourly sweep counts qualifying opportunities to learn where/how the pair expresses edge. A real live bot may operate with **one active position only**. Therefore overlapping opportunities that were useful for character discovery may be impossible to execute simultaneously.

After the 24-hour LONG map is complete, start a new lineage such as:

**One-Position Sequential LONG Execution Discovery**

Core live-like semantics:

1. move chronologically through time;
2. when flat, evaluate the frozen candidate activation rules;
3. take one eligible position according to a preregistered selector;
4. while that position is open, ignore all later entry signals;
5. exit using a preregistered, finite exit rule;
6. only after close may the system re-arm;
7. compute WR, PnL, PF, DD, streaks, holding time, exposure, and trade frequency from the **actual sequential trades**.

Do not use an unlimited “hold until eventually profitable” rule. Every execution experiment needs a finite, causal exit/maximum-hold condition.

The best starting ranges for execution discovery must come from the new pair's own 24-hour map—for example a contiguous cluster of formal PASS hours plus strong path-risk near-misses. Do not inherit ETH's time range.

---

## 12. When to search SHORT

Default order after learning from ETH:

1. complete pair-native **24h LONG character map**;
2. perform the first sequential one-position LONG execution study so the live semantics are understood;
3. then run SHORT as a **separate pair-native discovery lineage**, using the same scientific discipline but without assuming it is the mirror image of LONG;
4. eventually combine LONG and SHORT only after each side has independently earned its character and execution logic.

A future project may preregister SHORT-first or LONG+SHORT in another order, but the choice must be made before seeing the relevant results.

---

## 13. Required handoff for a new ChatGPT chat

When starting a fresh chat for another pair, instruct it to:

> Read `START_HERE_PAIR_NATIVE_CHARACTER_DISCOVERY.md` on `main` first. Follow the process, not ETH/BTC/SOL coordinates. Then inspect the target pair's existing branches/results, determine where its current discovery lineage stops, and continue with preregistered pair-native experiments. Keep OOS closed. Persist every material result. Complete the 24-hour character map before treating any hour as the pair's full character or moving to real-execution optimization.

A new chat should explicitly confirm these principles before running experiments:

- **method transfer, not character transfer**;
- **one hour at a time**;
- **full 24-hour sweep**;
- **formal gates stay frozen**;
- **near-miss != PASS**;
- **failure mechanism is recorded**;
- **execution discovery begins only after the temporal map is complete**.

---

## 14. ETH is a worked example, not a template

ETH E12A–E12X demonstrated why this process exists:

- the same state family can be strong in one hour and collapse in the next;
- payoff horizons can rotate sharply by hour;
- some FAIL hours can have higher PnL/WR than PASS hours but fail because of DD, loss clustering, anchor breadth, or era instability;
- full-gate PASS hours can cluster temporally;
- completing all 24 hours reveals information that stopping at the first winner would miss.

Use ETH only to understand the **logic of the methodology**. Never seed another pair with ETH's winning hours, state families, lookbacks, or holds unless the other pair independently rediscovers them under its own frozen sweep.

---

## 15. Canonical phase map

`DATA/AUDIT -> PREREGISTRATION -> 24H LONG CHARACTER SWEEP -> TEMPORAL MAP -> FAILURE TAXONOMY -> ONE-POSITION SEQUENTIAL LONG EXECUTION -> SHORT CHARACTER DISCOVERY -> SHORT EXECUTION -> SIDE COMBINATION -> OOS VALIDATION -> LIVE-SHADOW -> PRODUCTION REVIEW`

Do not skip directly from an attractive Development PnL to production.

---

**Canonical principle:**

> **Every pair must discover its own character. What we reuse is the scientific search engine, not yesterday's answer.**
