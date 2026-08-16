# BTC Temporal A5 — Champion Improvement Checkpoint

**Date:** 2026-08-16  
**Status:** A5.0–A5.3 COMPLETE — conditional protection improves the 1.35/0.80/6h parent; promising, not production-ready  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation:** 2023-12-02 to 2026-07-30 exclusive (971 days)  
**5m data:** Binance Futures archive, 279,648 / 279,648 rows = 100% coverage  
**Tuesday occurrences:** 139  
**Sizing reference:** $10 margin × 50x = $500 notional, fixed sizing, no compounding  
**Fee assumption:** 0.15% round-trip per position

## Frozen parent champion

Every Tuesday exact **06:00 WIB**:
- SELL
- TP **1.35%**
- SL **0.80%**
- max hold **6h**
- timeout exits at actual price
- same-5m TP/SL ambiguity adverse-first

Full parent result:
- trades: **139**
- net-positive: **79**
- net-negative: **60**
- net WR: **56.83%**
- net PnL: **+$95.73**
- expectancy: **+$0.6887/trade**
- PF: **1.431**
- max DD: **$31.64**
- max loss streak: **4**
- positive chronological blocks: **6/8**

---

# A5.0 — loss forensics

Parent exit reasons:
- TP: 42
- SL: 39
- timeout: 58

Winner path medians:
- MFE **1.3782%**
- MAE **0.2523%**

Loser path medians:
- MFE **0.3776%**
- MAE **1.0145%**

Separation becomes meaningful around 10–15m:

At 10m:
- winner median net path: -0.0252% (favorable to short)
- loser median net path: +0.0324% (adverse)
- winner taker bias: -0.0196
- loser taker bias: +0.0089

At 15m:
- winner net: -0.0603%
- loser net: +0.0462%
- winner MFE / MAE: 0.1702 / 0.0930
- loser MFE / MAE: 0.1083 / 0.1420

### Early-entry hypothesis mostly rejected
Only **3** SL losses later reached the original -1.35% SELL target after first hitting the +0.80% SL within the same 6h horizon. Delaying entry is therefore not the primary improvement path.

### Bad-exit capacity is meaningful
Among 60 negative trades:
- 38 had MFE >=0.30%
- 26 had MFE >=0.40%
- **23 had MFE >=0.50%**
- 16 had MFE >=0.60%
- 10 had MFE >=0.80%

Thus many eventual losses were profitable first.

### Wrong-direction oracle capacity is large but hard to identify robustly
At 10m, among 59 negative trades still open, a perfect oracle flip to BUY 0.8/0.8 would have made **43** total-positive. This is only theoretical capacity; causal identification was tested next.

---

# A5.1 — early flip and unconditional profit protection

Chronological selection split:
- discovery: first 83 Tuesdays
- validation: last 56 Tuesdays

## Early wrong-direction FLIP fails validation
Discovery-selected 10m flip rule improved discovery materially, but collapsed validation:
- discovery delta: **+$17.42**
- validation delta: **-$42.37**
- full PnL: **+$70.78** vs parent +$95.73

Conclusion: generic early BUY flip is regime-dependent and is not an upgrade.

## Profit protection proves WR can rise, but unconditional protection clips the edge
A coarse probe that protected +0.20% after MFE +0.50% showed ~70% WR but sacrificed much of the parent PnL. A5.2 corrected the execution model: if the next decision open has already retraced through the +0.20% lock, exit at the actual open rather than assuming an impossible stop fill.

Under corrected execution, protecting every trade that reaches +0.50% gives:
- WR **69.78%**
- PnL **+$50.77**
- 19 losses rescued
- 1 winner damaged

This confirms the real frontier: high WR is mechanically available, but unconditional protection cuts too many runners that generate the parent’s expectancy.

---

# A5.2 — conditional RUNNER vs PROTECT

Frozen management hinge:
1. enter the parent SELL normally at 06:00;
2. wait until a completed 5m candle first touches **+0.50% short MFE**;
3. decide only after that candle completes, at the next 5m open;
4. either RUNNER (leave TP1.35/SL0.80/6h unchanged) or PROTECT.

The strongest cross-period interpretable state is:

> after touching +0.50% favorable, if the trigger candle closes with only **<= +0.35%** short profit remaining AND cumulative MAE before/through that trigger was **>=0.20%**, protect the trade at **+0.20%**; otherwise keep it as a full runner.

Execution detail:
- protection starts from the next 5m decision point;
- if +0.20% has already been retraced through, exit at actual next-open price;
- no retrospective +0.20% fill is assumed.

## Improved full result

| Metric | Parent | A5.2 conditional protect |
|---|---:|---:|
| Trades | 139 | 139 |
| Net wins | 79 | **83** |
| Net losses | 60 | **56** |
| Net WR | 56.83% | **59.71%** |
| Net PnL | +$95.73 | **+$105.90** |
| Expectancy/trade | +$0.6887 | **+$0.7619** |
| Profit factor | 1.431 | **1.501** |
| Max DD | $31.64 | **$26.64** |
| Max loss streak | 4 | 4 |
| Positive blocks | 6/8 | 6/8 |

Intervention statistics:
- protection actions: **7**
- original negative -> positive: **5**
- original positive -> negative: **1**
- one additional positive trade remained positive but was clipped
- net PnL uplift: **+$10.17**

### Chronological split
Discovery first 83:
- parent +$32.90
- frozen rule +$38.20
- delta **+$5.31**

Validation last 56:
- parent +$62.84
- frozen rule +$67.70
- delta **+$4.86**

Thus the same frozen rule improves both periods.

---

# A5.3 — frozen robustness

## Eight chronological blocks
Rule action/delta by block:
- B1: 1 action, +$5.00
- B2: no action
- B3: 2 actions, +$0.31 (contains one rescued loss and one damaged winner)
- B4: no action
- B5: 1 action, +$1.09
- B6: 2 actions, +$5.26
- B7: 1 action, -$1.49
- B8: no action

The uplift is therefore not generated by one calendar block only, although intervention N is still small.

## Year view
- 2024: 3 actions, delta **+$5.31**
- 2025: 4 actions, delta **+$4.86**
- 2026: no actions through July

## Leave-one-action-out sensitivity
Total frozen PnL is +$105.90. If either of the two largest +$5 rescue events is removed, PnL remains **+$100.90**, still above the +$95.73 parent. Hence the entire improvement is not dependent on a single best event.

## Local plateau
Nearby thresholds remain positive:
- weak-close 0.35 / MAE0.20: **+$105.90**, WR59.71, PF1.501
- weak-close 0.40 / MAE0.20: **+$105.90**, WR59.71, PF1.501
- weak-close 0.45 / MAE0.20: +$104.51
- weak-close 0.35 / MAE0.30: +$102.39
- weak-close 0.30 / MAE0.20: +$101.30

This is a local behavior region rather than a one-value numerical spike.

---

# Interpretation

The champion’s main remaining weakness is **not predominantly wrong initial direction** and is **not predominantly entry too early**.

The most useful repeatable failure state found so far is:

`SELL works enough to reach +0.50% -> but the move gives back strongly by trigger close -> the same trade previously experienced meaningful adverse pressure -> odds of later giveback are elevated`

This allows a small subset of trades to be protected while preserving most large 1.35% runners.

The important distinction is:
- protecting ALL +0.50% trades => WR ~69.8%, but PnL only ~$50.8;
- protecting only the frozen failure state => WR **59.71%** and PnL **$105.90**, both better than parent.

Therefore the high-value research direction is **selective runner-vs-protect intelligence**, not shrinking TP, widening SL, delaying every entry, or flipping direction broadly.

# Verdict

**A5.2 conditional protection is the new research champion, provisionally:**
- same 139 Tuesday entries
- same 1.35/0.80/6h parent geometry
- WR improves 56.83% -> **59.71%**
- PnL improves +$95.73 -> **+$105.90**
- PF improves 1.431 -> **1.501**
- DD improves $31.64 -> **$26.64**

However only 7 historical interventions fire, so this remains **promising research**, not production-ready. Before live integration, the rule should be frozen and tested on forward/OOS data or independently across another analogous temporal cluster (e.g. Friday BUY) to determine whether the runner/protect mechanism generalizes.
