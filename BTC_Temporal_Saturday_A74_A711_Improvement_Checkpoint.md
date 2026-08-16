# BTC Temporal Saturday 18 WIB — A7.4 to A7.11 Improvement Checkpoint

**Date:** 2026-08-16  
**Status:** FORENSICS COMPLETE FOR THIS PASS — FROZEN PARENT UNCHANGED  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation:** 2023-12-02 to 2026-07-30 exclusive (971 days)  
**Saturday occurrences:** 139  
**Data:** Binance Futures 5m, 100% coverage  
**Sizing reference:** $10 margin × 50x = $500 fixed notional  
**Base fee:** 0.15% round trip  
**Funding:** historical BTCUSDT funding, canonical A7.3 fallback methodology  
**Research only:** no live BBC code modified

---

## Frozen parent (unchanged)

**Saturday 18:00 WIB BUY — TP2.6% / SL1.2% / max hold18h**

Funding-adjusted canonical economics:
- 139 trades
- 65 net-positive / 74 net-negative
- WR **46.76%**
- net **+$87.20**
- expectancy **+$0.6273/trade**
- PF **1.364**
- max DD **$45.12**
- max loss streak **7**
- **6/8 positive blocks**
- discovery first83: **+$52.67**
- validation last56: **+$34.53**

This remains the official Saturday research parent after A7.4–A7.11. No post-entry modification tested in this pass was robust enough across both chronological halves to replace it.

---

# A7.4 — Loss-path forensics

### Parent exit mix
- TP: 14
- SL: 22
- timeout: 103
- ambiguous same-bar SL: 0

### Path medians

| Group | MFE | MAE |
|---|---:|---:|
| Winner | **1.4102%** | **0.2348%** |
| Loser | **0.3617%** | **0.8224%** |

The separation is large: winners typically develop substantial favorable excursion while losers experience much deeper adverse excursion.

### Giveback capacity among 74 funding-adjusted losers
- MFE >=0.3%: **48**
- MFE >=0.5%: **28**
- MFE >=0.8%: **9**
- MFE >=1.0%: 6
- MFE >=1.2%: 4
- MFE >=1.5%: 1
- MFE >=2.0%: 0

Thus roughly **37.8% of parent losers first reach at least +0.5% favorable excursion**, providing meaningful theoretical profit-protection capacity.

### Early-entry diagnosis
Among parent SL losses, the number that subsequently reached the original +2.6% BUY TP inside the original 18h horizon was:

**0**

Therefore the primary issue is not “BUY direction eventually works after exact 18:00 entry gets stopped.”

### Early wrong-direction oracle capacity
Among losers still open, a hypothetical SHORT from early checkpoints often becomes net-positive. Example at 30m:
- losses still open: 74
- SHORT 1.2/1.2 positive: 44
- SHORT 2.6/1.2 positive: 44

This is oracle capacity only; it does not prove a causal classifier exists.

### Early winner/loser feature separation
At 15m median:
- winner progress: +0.0083%
- loser progress: -0.0281%
- winner taker edge: +0.0244
- loser taker edge: -0.0214

At 60m median:
- winner progress: +0.0754%
- loser progress: -0.0417%
- winner taker edge: +0.0169
- loser taker edge: -0.0174
- winner distance EMA20: +0.0167%
- loser distance EMA20: -0.0165%

### Pre-entry descriptive tendency
Saturday winners tend to enter after more weakness:
- winner day-position median 0.4514 vs loser 0.6244
- winner pre1 -0.0600% vs loser +0.0244%
- winner pre4 -0.0955% vs loser +0.0036%
- winner distance EMA20 -0.0224% vs loser +0.0019%
- winner is farther from HOD than loser

Interpretation: Saturday temporal BUY appears more like **rebound-from-weakness / positive drift** than a simple trend-chase signal.

---

# A7.5 — Early failure CUT / FLIP

A compact causal family was tested at completed 15/30/60/120m checkpoints using price progress, taker flow, EMA20 relation/slope. Candidates were selected on discovery only; validation was then evaluated. CUT and SHORT flips included realistic second round-trip fee where applicable and historical funding.

### Best discovery FLIP26 example
60m rule using adverse progress + negative taker flow + negative EMA20 slope:
- discovery delta: **+$15.16**
- validation delta: **-$26.67**
- full delta: **-$11.51**

### Best discovery CUT family
- discovery improved
- validation deteriorated by approximately the same magnitude
- full improvement effectively flat while WR/stability worsened

**Verdict: REJECTED.**

The descriptive early separation is real, but the actionable mapping is non-stationary across the chronological split.

---

# Funding parity audit

The first A7.5 implementation skipped funding events whose timestamps did not map to an exact 5m open, producing an approximately +$1.41 optimistic baseline difference. A7.5b traced this to 65 trades.

Canonical A7.3 behavior uses entry price as fallback proxy when the funding timestamp lacks an exact 5m-open match. A7.5 was patched and rerun.

After patch:
- canonical parent net restored exactly to **+$87.20**
- WR restored to **46.76%**

All later Saturday work uses the canonical funding behavior.

---

# A7.6 — Favorable-hinge statistics

Pure statistics; no management change.

### +0.3% hinge
111 trades reached the hinge. Winner and loser states are very similar at that point; little useful discrimination.

### +0.5% hinge
89 trades reached it causally before full SL:
- 63 eventual winners
- 26 eventual losers

Full medians remain fairly similar, though validation losers show more prior adversity and more EMA20 overextension.

### +0.8% hinge
61 trades:
- 52 winners
- 9 losers

At +0.8%, loser exhaustion becomes more visible:
- winner prior MAE median: **0.1424%**
- loser prior MAE median: **0.2203%**
- winner distance above EMA20: **0.3286%**
- loser: **0.4498%**

Validation taker flow at the +0.8 hinge:
- winner approximately +0.0205
- loser approximately -0.0015

Interpretation: later-stage losers can look more overextended/exhausted, but sample size is small.

---

# A7.7 — Giveback sequence statistics

The strongest transferable behavioral observation in this pass was **giveback speed after +0.5%**.

After first reaching +0.5%, first completed close <=+0.4%:
- full winner median: **15m**
- full loser median: **5m**
- validation winner median: **40m**
- validation loser median: **5m**

After +0.5%, first close <=+0.3%:
- full winner median: **50m**
- full loser median: **30m**
- validation winner median: **105m**
- validation loser median: **30m**

Important EMA finding: fast giveback losers often remain above/near EMA20, while eventual winners may pull back below EMA and later recover. Therefore a naive `below EMA = failed BUY` rule is unsafe for Saturday and would cut valid runners.

---

# A7.8 — Fast-giveback classifier

Classification only. Hinge fixed at +0.5%. Candidate rules used giveback speed to +0.4/+0.3 with optional EMA20 context.

### C1: <=+0.4 within 5m
Discovery:
- 20 signals
- 8 losers /12 winners
- loser precision 40.0%

Validation:
- 10 signals
- 7 losers /3 winners
- loser precision **70.0%**

Full:
- 30 signals
- 15 losers /15 winners

Although raw precision is not high full-sample, C1 enriches loser incidence above the conditional +0.5-hinge base rate in both chronological halves.

### C2: <=+0.3 within 30m
Discovery:
- 22 signals
- 8 losers /14 winners

Validation:
- 7 signals
- 6 losers /1 winner

Again the relationship strengthens sharply in the recent validation regime.

EMA20 context did not consistently improve classification beyond giveback speed itself.

---

# A7.9 — Causal profit-lock test

C1/C2 were converted into real-style management tests. Signal is recognized after a completed 5m bar; action occurs from the next 5m open. If price is already beyond a proposed lock at decision time, simulator exits at actual decision-open price rather than inventing a missed stop fill. Otherwise a protective stop is armed while TP2.6 remains alive.

### C1 + lock +0.30%
This is the most interesting configuration economically:
- full WR: **57.55%**
- full net: **+$89.15**
- PF: **1.434**
- max DD: **$43.25**
- max loss streak: **5**
- 6/8 positive blocks
- actions: 30
- parent losses converted positive: **15**
- parent winners converted negative: **0**
- clipped positive winners: 10

Compared with parent:
- WR +10.79 percentage points
- PnL +$1.95
- PF improves
- drawdown and losing streak improve

However the chronological economics disagree sharply:
- discovery delta: **-$18.68**
- validation delta: **+$20.63**

Therefore this is **not frozen as an upgrade** despite the attractive full-sample WR.

C2 protection is materially worse full-sample because it clips too many historical runners.

---

# A7.10 — Runner-recovery forensics

For the 30 C1-triggered cases:
- 15 eventual parent winners
- 15 eventual parent losers

Starting from the next 5m open after the trigger, recovery back to +0.5% before deterioration to +0.3% occurred:
- full winners: **6/15**
- full losers: **2/15**
- discovery winners: **5/12**
- discovery losers: **1/8**
- validation winners: **1/3**
- validation losers: **1/7**

Thus a return to +0.5% before the +0.3% protection boundary is meaningfully enriched for eventual winners and offers causal recovery capacity.

---

# A7.11 — C1 protection + runner recovery

State machine tested:
1. parent BUY reaches +0.5%
2. completed 5m gives back to <=+0.4% within 5m (C1)
3. +0.30% protection boundary becomes active
4. if protection is hit first -> protected exit
5. if price recovers to threshold first -> cancel protection and restore original TP2.6 / SL1.2 runner
6. same 5m touches both -> protection wins

Best full result in tested recovery neighborhood came from recovery around **+0.55%**:
- WR **56.83%**
- net **+$91.11**
- expectancy **+$0.6555/trade**
- PF **1.436**
- max DD **$41.78**
- max loss streak **5**
- 6/8 positive blocks
- full delta vs parent **+$3.91**
- 14 parent losses rescued to positive
- 0 parent winners turned negative
- 7 runner recoveries; 6 belonged to original winners, 1 to an original loser

But chronological economics remain non-stationary:
- discovery delta **-$19.94**
- validation delta **+$23.85**

Recovery thresholds around +0.50 to +0.55 improve the full result, but none solve the discovery-vs-validation disagreement.

**Verdict: PROMISING RECENT-REGIME MANAGEMENT, NOT A FROZEN ALL-HISTORY UPGRADE.**

---

# Final verdict of this pass

Saturday **can** be analyzed deeply like Tuesday, and the analysis materially explains the low headline WR:

1. The frozen parent is a long-horizon positive-expectancy runner with low WR by design.
2. Entry-too-early-after-stop is not the main problem.
3. A large subset of losers first becomes profitable; 28/74 losers reach at least +0.5% MFE.
4. Fast giveback after +0.5% is the most consistent post-entry failure behavior discovered.
5. Aggressive early CUT/FLIP is non-stationary and rejected.
6. C1 fast-giveback protection can mechanically raise WR to roughly 57.5% while keeping full PnL near/slightly above parent, but it clips historical large winners.
7. Runner recovery recovers part of that lost magnitude and reaches +$91.11 / 56.83% WR full-sample.
8. Crucially, these management layers hurt the earlier discovery period and strongly help the recent validation period. This regime asymmetry prevents promotion to frozen champion.

## Official status after A7.11

**Keep the frozen Saturday parent unchanged:**

> Saturday 18:00 WIB BUY / TP2.6% / SL1.2% / max18h  
> 139 trades / WR46.76% / +$87.20 / PF1.364 / 6/8 blocks

Keep A7.9/A7.11 as **conditional recent-regime candidates**, not live rules.

## If Saturday research is resumed

Do **not** tune more lock/recovery thresholds on the same full sample. The next justified research question is a causal **regime-state detector** that determines when the fast-giveback protection family should be active. That detector must be derived without using future management outcome and should be evaluated walk-forward. Until such a detector exists, the original Saturday frozen parent is the robust reference.
