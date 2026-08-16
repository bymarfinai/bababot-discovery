# BTC Temporal A2 — Dynamic Sequence Discovery Checkpoint

**Date:** 2026-08-16  
**Status:** A2/A2.1 DISCOVERY COMPLETE — >70% dynamic candidates found; not production-ready yet  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Data:** 15m Binance Futures candles from Railway historical DB  
**Window:** 971 days, 93,216 / 93,216 candles = **100% coverage**  
**Tuesday occurrences:** 139  

## Research intent

Improve the strongest A1 temporal prior by learning causal market paths inside the temporal window. The goal is to find the best usable version of the edge, not to invalidate the A1 anomaly.

Architecture:

`TIME PRIOR -> PRE-WINDOW CONTEXT -> COMPLETED 15M EVENT SEQUENCE -> SELL / WAIT`

All A2 entries occur on the **next 15m open after the completed trigger bar**. No trigger candle is used as its own entry. Live BBC code/state is untouched.

---

## A1 parent

Tuesday 06:00 WIB SELL baseline over 971d:

| Horizon | N | Directional WR | Median MFE | Median MAE | MFE/MAE |
|---|---:|---:|---:|---:|---:|
| 30m | 139 | **64.75%** | 0.2293% | 0.1557% | 1.4725 |
| 240m | 139 | **64.03%** | 0.7194% | 0.4012% | 1.7933 |

The A2 task was to convert this fixed-clock prior into a dynamic SELL/WAIT sequence.

---

# A2 first pass

A2 tested a small, interpretable causal vocabulary inside Tuesday 06:00–08:00:

- HOD sweep/reject
- previous-1h high reject
- bearish rejection
- previous-1h-low breakdown acceptance
- bearish range expansion
- two consecutive bearish bars
- loss of 06:00 window open after trading above it (`OPEN_LOSS`)
- failed HOD acceptance
- simple context combinations with prior 1h/4h direction and daily-range location

There were 80 rule × horizon candidates. No healthy >=70% directional candidate appeared in this first pass, but one parent path stood out on **executable geometry**:

## Parent selected for refinement

`UPPER_HALF__OPEN_LOSS`

Definition:
1. Tuesday 06:00–08:00 WIB bearish temporal prior is active.
2. At 06:00, BTC is in the **upper half of the local day's HOD/LOD range known so far**.
3. Inside the window, price trades above the 06:00 open.
4. A completed bearish 15m candle closes back below the 06:00 open.
5. SELL entry = next 15m open.

A2 results:

### 120m
- N = 62
- directional WR = **66.13%**
- MFE/MAE = **1.5816**
- symmetric ±0.5% first-touch = **33 favorable / 17 adverse = 66.00%**

### 240m
- N = 62
- directional WR = **63.93%**
- median MFE = **0.8838%**
- median MAE = **0.3851%**
- MFE/MAE = **2.2948**
- symmetric ±0.5% first-touch = **41 / 19 = 68.33%**
- symmetric ±0.8% first-touch = **34 / 15 = 69.39%**

This was deepened in A2.1 rather than discarded.

---

# A2.1 refined dynamic sequence

A2.1 froze the parent state and tested only coherent causal refinements:

- trigger timing (early <=06:30, exact 06:15, exact 06:30)
- prior 24h direction
- prior 7d direction
- same-bar previous-1h-low breakdown
- same-bar bearish rejection
- same-bar range expansion
- prior HOD / previous-1h-high attack states

96 rule × horizon combinations were evaluated.

Result counts at the endpoint's discovery threshold:
- directional >=70% candidates: **9**
- ±0.5% first-touch >=70% candidates: **15**
- ±0.8% first-touch >=70% candidates: **18**

Small-sample rows are not treated as final winners. The most useful candidates are below.

---

## Candidate A — EARLY parent state (best sample / execution balance)

Rule:

`Tuesday temporal SELL prior -> upper-half day range -> trades above 06:00 open -> loses 06:00 open on a completed bearish bar by 06:30 -> SELL next 15m open`

240m results:
- N = **48**
- directional WR = **68.09%**
- median signed return = **+0.4029%** in SELL direction
- median MFE = **0.8992%**
- median MAE = **0.3425%**
- MFE/MAE = **2.6249**
- positive blocks >50% = **6/8**
- blocks >=60% = **6/8**
- blocks >=65% = 4/8
- median block WR = **72.85%**

Executable symmetric first-touch:
- **±0.5%: 34 favorable / 14 adverse = 70.83%**, decisive N=48
- **±0.8%: 29 / 10 = 74.36%**, decisive N=39; 9 no-touch
- ±1.0%: 20 / 10 = 66.67%

**Interpretation:** current best balance between sample size, causal execution, and >70% WR.

---

## Candidate B — Exact 06:30 trigger

Rule:

Parent `UPPER_HALF__OPEN_LOSS` is completed specifically on the **06:30 WIB 15m candle**; SELL enters next 15m open.

240m results:
- N = **32**
- directional WR = **75.00%** (24W / 8L)
- median signed return = **+0.3812%**
- median MFE = **0.8824%**
- median MAE = **0.2655%**
- MFE/MAE = **3.3236**
- positive blocks = **7/8**
- blocks >=60% = **7/8**
- blocks >=65% = **6/8**
- median block WR = **73.34%**
- minimum block WR = **40.00%**

Block directional WR:
`60%, 100%, 40%, 66.67%, 66.67%, 100%, 80%, 100%`

Executable:
- ±0.5% = 21 / 10 = **67.74%**
- **±0.8% = 19 / 6 = 76.00%**, decisive N=25
- ±1.0% = 12 / 6 = 66.67%

**Interpretation:** strong direction + strong 0.8% excursion. This is currently one of the clearest precise-timing discoveries.

---

## Candidate C — Prior 24h UP + early reversal

Rule:

`BTC up over prior 24h at 06:00 -> Tuesday SELL prior -> upper-half daily location -> early (<=06:30) loss of 06:00 open -> SELL next 15m open`

240m results:
- N = **32**
- directional WR = **74.19%**
- median signed return = **+0.4588%**
- median MFE = **0.8838%**
- median MAE = **0.2440%**
- MFE/MAE = **3.6226**
- positive blocks = 6/8
- blocks >=60% = 6/8
- blocks >=65% = 5/8
- median block WR = **87.50%**

Executable:
- **±0.5% = 24 / 8 = 75.00%**, decisive N=32
- **±0.8% = 19 / 8 = 70.37%**, decisive N=27
- ±1.0% = 57.89%

**Interpretation:** extremely coherent market story: prior-day rally/strength + upper location + early Tuesday failure/reversal. This is a high-priority dynamic state candidate.

---

## Candidate D — Prior 7d UP + early reversal

240m:
- N = **23**
- directional WR = **72.73%**
- MFE/MAE = **2.9700**
- positive blocks = **7/8**
- blocks >=60% = **7/8**
- blocks >=65% = 6/8
- min block WR = 40%

Executable:
- **±0.5% = 18 / 5 = 78.26%**
- **±0.8% = 14 / 5 = 73.68%**

Promising, but lower N than Candidate C.

---

## Candidate E — Same-bar previous-1h-low breakdown

Parent OPEN_LOSS trigger candle also closes below the previous-1h low.

240m:
- N = **38**
- directional WR = 63.16%
- MFE/MAE = **2.6433**

Executable:
- **±0.5% = 26 / 10 = 72.22%**
- **±0.8% = 21 / 9 = 70.00%**

Interpretation: structural breakdown improves first-touch execution even when four-hour close direction is less impressive.

---

## Candidate F — Early + same-bar breakdown (high-quality, small sample)

Rule:

Parent OPEN_LOSS occurs by <=06:30 and the trigger candle simultaneously closes below the previous-1h low.

240m:
- N = **18**
- directional WR = **77.78%**
- median MFE = **1.0373%**
- median MAE = **0.2212%**
- MFE/MAE = **4.6887**

Executable:
- ±0.5% = **15 / 3 = 83.33%**
- ±0.8% = **14 / 2 = 87.50%**

This is not crowned because N=18 and individual block counts are very small. It remains a strong subpattern for future accumulation/validation.

---

## Candidate G — Same trigger bar bearish rejection

240m:
- N = **39**
- directional WR = **71.79%**
- MFE/MAE = **2.6324**
- positive blocks = 6/8
- blocks >=60% = 6/8
- blocks >=65% = 5/8

But symmetric first-touch is weaker:
- ±0.5% = 56.76%
- ±0.8% = 66.67%

Interpretation: good end-horizon directional state, weaker fixed-target execution geometry.

---

# Current ranking

For the objective of a causal, executable, >70% BTC setup with usable sample:

1. **EARLY <=06:30 parent** — N=48; ±0.5% **70.83%**, ±0.8% **74.36%**. Best sample/quality balance.
2. **Prior 24h UP + EARLY parent** — N=32; directional **74.19%**, ±0.5% **75.00%**, MFE/MAE 3.62. Best coherent context-enhanced rule.
3. **Exact 06:30 parent trigger** — N=32; directional **75.00%**, ±0.8% **76.00%**, MFE/MAE 3.32. Best precise-time rule.
4. **Same-bar breakdown** — N=38; ±0.5% **72.22%**, ±0.8% **70.00%**. Strong structural-execution confirmation.
5. **Prior 7d UP + EARLY** — N=23; directional 72.73%, ±0.5% 78.26%; lower sample.
6. **EARLY + same-bar breakdown** — N=18; spectacular 77.78–87.50%, but too small to use as primary evidence.

---

# Important caveat / unfinished work

A2.1 is **discovery on the full 971-day history**. The result establishes that dynamic temporal conditioning can lift the A1 ~64–65% prior above 70% in several causal subsets, but it is not yet a production acceptance result.

Several candidates show weak chronological blocks around the middle of the history while later blocks are much stronger. The next phase should therefore rank these frozen candidates on robustness/generalization rather than create an uncontrolled new feature stack.

Recommended next steps:

1. Freeze Candidates A/B/C/E without changing definitions.
2. Run rolling / block-wise candidate comparison and regime-forensic analysis of strong vs weak blocks.
3. Apply the same **temporal-conditioned sequence architecture** independently to the Friday 15:00–17:00 BUY cluster to test generalization.
4. Only after a rule survives this step, model fee/slippage and final TP/SL/PnL.

## Core discovery

Potential A has evolved from:

`Tuesday 06:00 = SELL`

into a causal dynamic path such as:

`Tuesday bearish prior -> upper-half daily location -> early failed strength above 06:00 open -> close back below open -> SELL next 15m open`

and, in its strongest context-enhanced form:

`prior 24h UP -> Tuesday upper-half location -> early loss of 06:00 open -> SELL next 15m open`

This is the intended dynamic-sequence behavior: the clock provides the prior; actual price path decides SELL versus WAIT.
