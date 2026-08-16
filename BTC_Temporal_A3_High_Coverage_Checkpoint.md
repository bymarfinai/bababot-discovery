# BTC Temporal A3 — High-Coverage Dynamic Direction Checkpoint

**Date:** 2026-08-16  
**Status:** A3 HIGH-COVERAGE DISCOVERY COMPLETE — forced BUY/SELL did not reach 70%; raw Tuesday temporal prior remains stronger  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation window:** 971 days, 2023-12-02 00:00 UTC to 2026-07-30 00:00 UTC exclusive  
**15m parity:** 93,216 / 93,216 candles = 100% coverage  
**5m parity:** 279,648 / 279,648 candles = 100% coverage  
**Tuesday occurrences:** 139

## Research intent

The user explicitly rejected a filter-centric interpretation of A2. The desired architecture is:

`TEMPORAL WINDOW -> DEEP CAUSAL PATTERN ANALYSIS -> BUY or SELL`

The goal is to trade almost every occurrence of the recurring temporal window rather than reduce 139 Tuesdays to a small premium subset. Therefore A3 intentionally tests **high-coverage forced direction**. WAIT is disabled/minimized by design.

Core requirements during A3:
- preserve causality / no future data
- use walk-forward or prior-history learning only
- every evaluated Tuesday receives BUY or SELL
- compare against the exact same-entry fixed temporal baseline
- distinguish future-close directional accuracy from executable TP-vs-SL first-touch accuracy
- do not declare tiny decisive samples as success

---

## Parent A1 temporal edge — independent parity confirmation

Exact Tuesday 06:00 WIB SELL baseline over 971 days:

### 30-minute close direction
- N = **139**
- 90 wins / 49 losses
- WR = **64.75%**
- 7/8 chronological blocks >50%

### 240-minute close direction
- N = **139**
- 89 wins / 50 losses
- WR = **64.03%**

### Symmetric ±0.5% first-touch within 240m
- all Tuesday entries = **139**
- favorable SELL side first = **84**
- adverse BUY side first = **45**
- no-touch = **10**
- resolved = **129 / 139 = 92.81%**
- first-touch WR = **65.12%**
- block WR = `43.75, 70.59, 64.71, 56.25, 58.82, 86.67, 64.29, 76.47`
- 7/8 blocks >50%; 5/8 >=60%

This baseline was reproduced from official Binance 5m archives independently of the Railway 15m database.

---

# A3 experiment ladder

## A3 — Tuesday-only walk-forward at 06:30

Observation: completed 06:00 and 06:15 15m candles.  
Decision/entry: 06:30 WIB.  
Every post-warmup Tuesday forced BUY/SELL.

Best dynamic directional result was approximately **61.02% (72/118)** at 240m, only marginally above same-entry always-SELL (~60.17%). No healthy >=70% candidate.

Interpretation: two first 15m bars do not contain enough information to reliably flip the temporal prior at high coverage.

## A3.1 — deeper observation checkpoints through 08:00

Fixed decision checkpoints from 06:15 through 08:00; 119/119 post-warmup Tuesdays still forced BUY/SELL.

Best forced-direction result remained roughly **59–60%**. Delaying the decision did not create a high-accuracy direction classifier.

## A3.2 — cross-day path learning

Instead of learning only from ~139 Tuesdays, the learner used all prior calendar days at the same 06:00–08:00 window to learn generic price-path mechanics, while evaluation remained Tuesday-only and 139/139 forced BUY/SELL.

Best dynamic result: approximately **60.43% (84/139)**. More generic OHLC path examples did not solve the classification problem.

## A3.3 — 15m taker flow / absorption

Added Binance taker-buy ratio, changes in aggression, quote-volume expansion, buyer/seller failure, and simple HOD/LOD trap/absorption states while maintaining 139/139 trade coverage.

Best forced-direction result: approximately **59.71% (83/139)**. Aggregated 15m order-flow information did not raise high-coverage direction toward 70%.

## A3.4 — Potential-2-style 5m event sequence

Moved to true 5m event-state language:
- frozen HOD/LOD and previous-1h high/low
- wick attacks vs close acceptance
- two-close acceptance
- reclaim after attack/acceptance
- first liquidity side attacked
- double sweep
- taker-aggression trajectory
- buyer/seller absorption
- range/volume expansion
- event-path ordering

Data: 279,648 / 279,648 5m candles, 100% coverage.  
Evaluation: 139/139 Tuesday BUY/SELL.

Best dynamic directional engine:
- `WF_5M_STATE_MIN20`
- decision 06:45 WIB
- horizon 240m
- 81W / 58L = **58.27%**
- all 8 blocks >50%, but only one >=60%

Same-entry always-SELL at 06:45 was **58.99%**, so dynamic event classification did not improve it.

### Critical timing discovery

The original temporal edge starts at **06:00 WIB**. Waiting until 06:30–07:00 consumes part of that edge:
- exact 06:00 baseline, 240m: **64.03%**
- 06:30 same-entry baseline, 240m: about **58.27%**
- 06:45 same-entry baseline, 240m: about **58.99%**
- 07:00 same-entry baseline, 240m: about **57.55%**

Therefore the correct high-coverage architecture should decide from information available **before 06:00**, not spend the edge waiting for post-window confirmation.

## A3.5 — pre-window 5m path -> exact 06:00 entry

Decision/entry returned to exact 06:00 WIB. Features used only completed 5m data from 30/60/120/240 minutes before 06:00, including recent structural attacks/reclaims, daily location, HOD/LOD recency, taker flow, absorption, trend efficiency, and range/volume expansion.

Best dynamic close-direction result:
- engine `WF_PRE5M_TOP5`
- lookback 30m
- outcome 30m
- 88W / 51L = **63.31%**
- BUY 18 / SELL 121
- 7/8 blocks >50%; 5/8 >=60%
- average signed return +0.0862%

Raw always-SELL at the same entry/horizon remained better on WR:
- **90W / 49L = 64.75%**

Interesting nuance: the dynamic model improved average signed return magnitude while losing two directional wins. That suggests pre-window state contains some information about move magnitude, but not enough to reliably identify the SELL-loser Tuesdays as BUY days.

---

# A3.6 — direct TP-vs-SL first-touch classifier

This was the most trading-native A3 test.

Instead of asking whether BTC closes up/down after a horizon, the learner directly predicts which side of a symmetric trade is touched first within 4h. Every Tuesday still enters at exact 06:00 WIB and is assigned BUY or SELL. No WAIT filter.

Thresholds tested as direct objectives:
- ±0.3%
- ±0.5%
- ±0.8%
- ±1.0%

Pre-window lookbacks:
- 30m
- 60m
- 120m
- 240m

Dynamic engines:
- walk-forward token evidence TOP3/TOP5/TOP8/ALL
- hierarchical first-touch state learners

### Result

**No candidate met >=70% WR with >=80% first-touch resolution.**

`viable70 = []`

### Most important ±0.5% comparison

Raw Tuesday SELL:
- trades = **139**
- resolved = **129**
- no-touch = **10**
- resolution = **92.81%**
- wins = **84**
- losses = **45**
- WR = **65.12%**

Best A3.6 dynamic rows at ±0.5% were below this baseline. For example:
- `WF_FT_ALL`, lookback 60m: 77W / 52L = **59.69%**, BUY 47 / SELL 92
- `WF_FT_TOP3`, lookback 120m: 77W / 52L = **59.69%**, BUY 50 / SELL 89
- multiple TOP5/TOP8 variants were around **58.91%**

The learner did flip a substantial number of Tuesdays to BUY, but those flips were not accurate enough; the raw bearish prior was stronger.

### Other thresholds

At ±0.3%:
- raw SELL = 83W / 55L = **60.14%**, 138/139 resolved
- best dynamic state rows also ~**60.14%**, effectively no improvement

At ±0.8%:
- raw SELL = 54W / 34L = **61.36%**, only 88/139 resolved
- best dynamic rows were about **59.09%** with the same resolution range

At ±1.0%:
- raw SELL = 44W / 27L = **61.97%**, only 71/139 resolved
- best dynamic TOP5 reached **63.38% (45W/26L)**, but resolution was only **51.08%**, far below the >=80% viability requirement

So the only apparent directional lift occurred at a threshold where almost half the Tuesday entries never resolved within 4h; it is not a healthy high-coverage result.

---

# A3 conclusion

The high-coverage hypothesis was tested seriously rather than converted into a filter:

`every Tuesday temporal window -> deep causal analysis -> BUY or SELL`

Across:
- Tuesday-only walk-forward analogues
- deeper observation timing
- cross-day generic path learning
- OHLC structural path states
- 15m taker-flow / absorption
- 5m Potential-2-style event sequences
- pre-window 5m state at the exact A1 entry
- direct symmetric TP-vs-SL first-touch classification

**none produced a robust >=70% forced-direction engine while preserving near-full Tuesday trade coverage.**

The strongest high-coverage information remains the raw temporal prior itself:
- 30m close SELL = **64.75%**
- 4h ±0.5% first-touch SELL = **65.12%** with 92.81% resolution

A2 demonstrated that causal path information *can* identify higher-quality subsets (70–76%+), but A3 demonstrates that the same information has not reliably converted the opposing Tuesday cases into high-accuracy BUY trades at full coverage.

This should **not** be interpreted as "Potential A is false." It means the current evidence supports a recurring bearish Tuesday edge, but not a reliable high-coverage direction-switching engine from the available BTC OHLC/taker-flow information.

---

# Best next research direction

Do not keep threshold-mining Tuesday indefinitely.

The highest-value next step is to apply the **same high-coverage dynamic-direction protocol** to the other A1 temporal clusters, especially:

1. **Friday 15:00–17:00 WIB BUY cluster** — stronger neighborhood structure and good short-horizon MFE/MAE.
2. Saturday 18:00 BUY.
3. Sunday 01:00 BUY.
4. Thursday 10:00 SELL as stability benchmark.

The portfolio objective becomes:

`multiple recurring temporal engines × high trade coverage per engine`

rather than forcing one Tuesday slot to manufacture both BUY and SELL states.

If one or more additional temporal windows remain ~64–65% at high coverage, frequency can be increased through **independent recurring clocks** rather than sacrificing edge quality inside a single clock. A separate later research track can revisit selective dynamic sub-states only if needed for premium-confidence trades.
