# BTC Temporal Saturday 18 WIB — Strict-Causal Improvement Checkpoint (A7.13b–A7.23)

**Date:** 2026-08-17 WIB  
**Status:** PROVISIONAL IMPROVED RESEARCH CHAMPION IDENTIFIED — NOT PRODUCTION/OOS PROVEN  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation:** 2023-12-02 to 2026-07-30 exclusive (971 days)  
**Saturday occurrences:** 139  
**Data:** Binance Futures 5m  
**Sizing reference:** $10 margin × 50x = $500 fixed notional  
**Base fee assumption:** 0.15% round trip  
**Funding:** historical BTCUSDT funding using canonical A7.3 methodology  
**Live BBC:** untouched

---

## 1. Official frozen parent baseline remains unchanged

Saturday 18:00 WIB BUY:
- TP **2.6%**
- SL **1.2%**
- max hold **18h**

Funding-adjusted baseline:
- 139 trades
- 65 positive / 74 negative
- WR **46.76%**
- net **+$87.20**
- expectancy **+$0.6273/trade**
- PF **1.364**
- max DD **$45.12**
- max loss streak **7**
- 6/8 positive chronological blocks
- discovery first83: **+$52.67**
- validation last56: **+$34.53**

This remains the frozen **parent** and reference baseline.

---

## 2. Strict-causality repair discovered in A7.13b

The earlier shared `state()` helper used EMA at the next decision candle index `j`. Because a decision is taken at the **open** of that candle, EMA at `j` would include that candle's close and therefore introduce one 5m candle of look-ahead.

A7.13b repaired this:
- checkpoint consists only of completed bars through `j-1`
- EMA7/EMA20 values end at `j-1`
- EMA slopes also end at `j-1`
- the actual open of `j` is allowed as the decision price
- action, if any, starts at that actual open

Any pre-A7.13b EMA classification numbers should therefore be treated as superseded by the strict-causal versions.

The repaired 60m failure state survived:
- `progress <= -0.10% + taker edge < 0`
- discovery eventual-loss precision **76.47%**
- validation **76.92%**
- full **76.67%**

A strict EMA20+slope variant also produced about 75% loss precision in both chronological halves.

However, classification quality did **not** imply a profitable action.

---

## 3. A7.14 — direct early thesis-failure action rejected

At 60m, CUT and compact SHORT flips were tested using strict-causal signals, actual next-5m-open execution, historical funding, and full fee accounting.

The warning state was informative, but direct action destroyed runner economics because several eventual large winners looked weak at 60m.

Example FLOW CUT:
- parent +$87.20 -> about **+$60.22**
- WR fell rather than improved
- DD worsened materially

Best compact FLIP family was also worse than the parent after two-leg fees/funding.

**Verdict:** 60m A1 signal is a **warning state, not an exit/flip state**.

---

## 4. A7.15 — late runner-failure diagnosis

At 360m, a strict-causal pattern became high precision:

`MFE >= +0.5% -> current progress <= +0.10% -> taker edge < 0`

- full: 5 signals / 4 eventual losses = **80% loss precision**
- discovery: 75%
- validation: 100%
- only one winner false positive

But this is usually too late to turn the position into a net-positive trade after the 0.15% fee assumption.

**Interpretation:** useful diagnosis, poor WR-rescue timing.

---

## 5. A7.16–A7.17 — lockable-zone discovery

A lockable zone was investigated while gross BUY profit was still roughly +0.20% to +0.40%.

Most balanced strict-causal candidate at 240m:
- prior MFE >= +0.50%
- current progress +0.20% to +0.40%
- cumulative observed taker edge < 0

A7.17 direct next-open exit on this broad condition:
- WR **46.76% -> 50.36%**
- net **+$87.20 -> +$94.35**
- PF 1.364 -> 1.421
- DD $45.12 -> about $33.14
- loss streak 7 -> 5
- 5 original losses converted positive
- 0 original winners converted negative

But chronological economics were mixed:
- discovery delta positive
- validation delta negative, driven mainly by a large validation runner that had already demonstrated much stronger MFE.

This led to A7.18 rather than promotion.

---

## 6. A7.18 — false-positive runner forensic

The nine broad A7.17 signals contained:
- 5 eventual parent losses
- 4 eventual parent winners

The major validation false-positive winner had already achieved roughly **+1.02% MFE** before the 240m failure signal.

All five eventual-loss signals had prior MFE only around **+0.55% to +0.70%**; none had reached +0.8%.

This aligned with the independently pre-existing A7.12 taxonomy boundary:
- C loss = MFE +0.5% to <+0.8%
- D/deep runner = MFE >=+0.8%

Therefore A7.19 tested the natural concept: protect only a **shallow runner**, while leaving a runner that has already proved >=+0.8% strength alone.

Important caveat: although +0.8% was an existing taxonomy boundary, its use as a management qualifier was finalized after inspecting A7.18. Thus A7.19 is same-sample-derived and not pristine untouched OOS proof.

---

# 7. A7.19 — PROVISIONAL IMPROVED SATURDAY CHAMPION

Frozen candidate rule:

1. Enter every Saturday at **18:00 WIB BUY** as before.
2. Original TP **2.6%**, SL **1.2%**, max hold **18h** remain unchanged.
3. After **240 completed minutes**, evaluate using only completed 5m data.
4. At the next 5m open, if all are true:
   - prior MFE >= **+0.50%**
   - prior MFE < **+0.80%**
   - current actual-open progress is **+0.20% to +0.40%**
   - observed taker-buy edge over the completed window is **negative**
5. Exit the BUY at that **actual next 5m open**.
6. Otherwise preserve the original runner.

There is no phantom entry, phantom TP, retrospective fill, or same-candle future information in this rule.

### Full 971-day result

| Metric | Frozen Parent | A7.19 Provisional |
|---|---:|---:|
| Entries | 139 | **139** |
| WR | 46.76% | **50.36%** |
| Net PnL | +$87.20 | **+$103.383** |
| Expectancy/trade | +$0.6273 | **+$0.7438** |
| PF | 1.364 | **1.462** |
| Max DD | $45.12 | **$33.136** |
| Max loss streak | 7 | **5** |
| Positive blocks | 6/8 | **6/8** |

Interventions:
- **8** actions total
- **5 parent loss -> positive**
- **0 parent winner -> negative**
- 3 positive winners were clipped but remained positive

### Chronological split

Discovery first83:
- WR **53.01%**
- PnL **+$66.588**
- PF **1.488**
- DD **$24.382**
- delta vs parent **+$13.921**
- 7 actions / 4 losses rescued

Validation last56:
- WR **46.43%**
- PnL **+$36.795**
- PF **1.420**
- DD **$18.046**
- delta vs parent **+$2.262**
- 1 action / 1 loss rescued

Thus the frozen candidate improves economics in both chronological halves, unlike the older A7.9/A7.11 management family.

---

## 8. A7.23 robustness audit of A7.19

### Natural MFE-boundary sensitivity

Upper caps **0.75 / 0.80 / 0.85 / 0.90** all produced **exactly the same eight actions and exact same result**:
- WR 50.36%
- PnL +$103.383
- PF 1.462

This means the result is not dependent on precise placement of the upper MFE cap inside that neighborhood.

### Checkpoint perturbation

Same logic evaluated at nearby fixed checkpoints:

- **210m:** 3 actions, WR47.48%, PnL **+$92.714**, discovery delta +$5.514, validation delta $0
- **240m:** 8 actions, WR50.36%, PnL **+$103.383**, discovery +$13.921, validation +$2.262
- **270m:** 5 actions, WR48.92%, PnL **+$98.811**, discovery +$9.870, validation +$1.740

The mechanism therefore does not disappear immediately when the exact 240m checkpoint is perturbed, although 240m is the strongest tested point.

### Leave-one-action-out

Removing any single intervention while keeping all others active leaves total PnL between roughly **+$95.99 and +$105.23**.

The worst leave-one-out result remains above the +$87.20 parent.

Thus the uplift is not dependent on one rescue event.

### Year distribution

- 2023 (only 5 trades): +$14.25 -> +$18.64
- 2024: +$35.60 -> +$44.26
- 2025: -$3.48 -> approximately **-$0.34**
- 2026 through July: unchanged +$40.83 because no A7.19 action fired

The rule does not create the underlying Saturday edge; it selectively improves a small subset of shallow-runner failures.

### Extra execution-cost stress

If extra cost is applied **only to the eight A7.19 intervention exits**:
- +0.02% extra: total about **+$102.58**
- +0.05%: **+$101.38**
- +0.10%: **+$99.38**

The management uplift therefore survives substantial additional intervention-specific cost in this sample.

If extra cost is instead charged to all 139 trades, total strategy expectancy naturally compresses, because the frozen parent itself has a moderate edge. Even at +0.10% extra on every trade, total PnL remains positive (~+$33.88) but block robustness drops.

---

## 9. A7.20–A7.21 — weak-pop family B researched and rejected for management

B taxonomy consists of 20 parent losses that reach +0.30% but never +0.50%.

A7.20 showed these losses give back quickly:
- after first +0.30%, close <=+0.25% median 5m full / 10m discovery / 5m validation
- close <=+0.20% median about 10m

However eventual winners also frequently make the same early pullback.

A strict-causal classifier:
`first +0.30 -> no +0.50 continuation yet -> completed close <=+0.25`
produced only:
- <=5m: **43.9% eventual-loss precision** full
- discovery 42.31%
- validation 46.67%
- 23 winner false positives

The <=10m version was similarly weak.

**Verdict:** do not manage family B with this sequence; it would clip too many valid runners.

---

## 10. A7.22 — deep-runner family D researched; no deployable failure signal yet

D consists of 9 losses that first demonstrate >=+0.8% MFE.

They tend to give back to +0.7 quickly, but valid large winners also frequently perform that pullback:
- D: 7/9 close <=+0.7 within 15m
- eventual winners: 24/52 do the same

EMA7/EMA20 loss/reclaim timing also overlaps heavily.

**Verdict:** no management layer added for deep runners. Preserve them rather than risk destroying the 2.6% payoff engine.

---

# Final research status after A7.23

### Frozen parent baseline
> Saturday 18:00 WIB BUY / TP2.6 / SL1.2 / max18h  
> 139 trades / WR46.76% / +$87.20 / PF1.364

### Provisional improved research champion
> Same 139 entries and same base geometry  
> + strict-causal 240m shallow-runner failure exit  
> **WR50.36% / +$103.383 / PF1.462 / DD$33.136 / LS5**

This is the strongest Saturday management variant found in the current strict-causal pass because it simultaneously:
- raises WR
- raises PnL and expectancy
- raises PF
- reduces drawdown
- reduces losing streak
- retains all 139 entries
- has positive delta in discovery and validation
- survives local boundary/checkpoint/cost/leave-one-out robustness checks.

### Caveat

A7.19 is still **same-sample research**, not pristine untouched OOS evidence. The +0.8 management qualifier was informed by A7.18 analysis even though +0.8 was already an independently defined A7.12 taxonomy boundary. Therefore:
- do not label it production-ready
- do not further retune it on the same 971-day sample
- next strong proof should come from truly unseen future Saturdays, another asset, or a pre-registered walk-forward/transfer test.

### Live implementation

No live code was modified. Any future implementation must use:
- actual exchange entry fill as price anchor
- completed 5m data only
- decision at the actual next 5m open/market fill
- historical/live exchange funding/fees as applicable
- no phantom MFE, EMA, entry, exit, TP, or retrospective fill.
