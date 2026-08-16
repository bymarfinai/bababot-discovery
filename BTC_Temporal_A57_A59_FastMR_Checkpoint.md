# BTC Temporal A5.7–A5.9 — Fast Mean-Reversion Checkpoint

**Date:** 2026-08-16  
**Status:** COMPLETE — fast mean-reversion state materially improves A5.2; promising research, not production-ready  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation:** 2023-12-02 to 2026-07-30 exclusive (971 days)  
**Tuesday occurrences:** 139  
**Data:** Binance Futures 5m, 100% coverage  
**Sizing reference:** $10 margin × 50x = $500 notional, fixed sizing, no compounding  
**Fee assumption:** 0.15% round-trip per position

## Frozen base geometry
Every Tuesday exact 06:00 WIB:
- SELL
- TP 1.35%
- SL 0.80%
- max hold 6h
- timeout at actual price

Static parent:
- 139 trades
- WR 56.83%
- PnL +$95.73
- PF 1.431
- max DD $31.64
- max loss streak 4
- 6/8 positive blocks

A5.2 balanced champion before this study:
- same 139 entries
- conditional +0.20 protection after +0.50 MFE when trigger-close progress <=0.35 and cumulative MAE >=0.20
- WR 59.71%
- PnL +$105.90
- PF 1.501
- max DD $26.64
- 6/8 positive blocks

---

# A5.7 — Giveback Sequence Forensics

A5.2 actions were kept first. Only hinge trades not touched by A5.2 were studied.

Among 88 untouched trades that had reached +0.50% MFE:
- 14 later negative under A5.2
- 74 positive

The key separation was not simply whether EMA7 was eventually reclaimed; it was **overextension plus speed of the mean-reversion**.

## Full untouched-hinge atlas

Eventual negatives (N14):
- hinge distance vs EMA7 median: **-0.3464%**
- hinge distance vs EMA20 median: **-0.4466%**
- EMA7 reclaim occurrence: 100%
- median EMA7 reclaim time from entry: 72.5m
- median two-close-above-EMA7 time: 92.5m
- pullback to <=+0.35 occurred in 100%
- pullback to <=+0.30 occurred in 100%

Eventual positives (N74):
- hinge distance vs EMA7 median: **-0.1904%**
- hinge distance vs EMA20 median: **-0.3020%**
- EMA7 reclaim occurrence: 75.68%
- median EMA7 reclaim time: 120m
- median two-close-above-EMA7 time: 140m
- pullback to <=+0.35 occurred in 56.76%
- pullback to <=+0.30 occurred in 48.65%

Validation was even more separated on speed:
- negative EMA7 reclaim median: 40m
- positive EMA7 reclaim median: 137.5m

Direct broad EMA exits still clipped too many runners and did not improve A5.2 cross-period.

Interpretation: the useful state is:

`strong downside overextension from EMA -> rapid giveback / mean-reversion`

rather than simply `EMA reclaim = exit`.

---

# A5.8 — Fast Mean-Reversion Rescue

Compact family tested:
- hinge EMA20 overextension thresholds 0.30 / 0.35 / 0.40%
- giveback events: pullback <=+0.35, pullback <=+0.30, EMA7 reclaim, two-close-above EMA7
- latency from hinge: 20 / 30 / 45 / 60m
- management: market exit or +0.20 profit lock while retaining TP1.35

A5.2 remains first priority; A5.8 only acts on A5.2-untouched hinge trades.

## Strongest balanced cross-period rule

> After the trade has reached +0.50% MFE, if the completed hinge candle is at least **0.40% below EMA20**, and within **60 minutes after the hinge** a completed 5m close gives back so short progress is **<=+0.30%**, then from the next 5m open arm a **+0.20% profit lock** while retaining the original TP1.35. If the +0.20 lock has already been lost at decision open, exit at that actual open.

### Result
- trades: **139**
- wins: **89**
- losses: **50**
- WR: **64.03%**
- net PnL: **+$120.27**
- expectancy: **+$0.8652/trade**
- PF: **1.638**
- max DD: **$26.64**
- max loss streak: **4**
- positive blocks: **7/8**

Incremental vs A5.2:
- PnL +$105.90 -> **+$120.27** (+$14.36)
- WR 59.71% -> **64.03%** (+4.32pp)
- 12 additional actions
- **6 A5.2-negative trades became positive**
- **0 A5.2-positive trades became negative**

Important nuance: zero positive->negative damage does NOT mean no winners were clipped. Two large A5.2 winners were reduced to small positive locks, which is visible in intervention deltas. The rescued losses outweighed those clips at the frozen 0.40 threshold.

---

# A5.9 — Frozen Robustness

No re-selection of the A5.8 winner.

## Chronological split
Discovery first 83:
- A5.2 WR 54.22%, PnL +$38.20
- A5.9 WR **57.83%**, PnL **+$49.97**
- 7 actions, 3 rescued, 0 positive->negative
- delta **+$11.77**

Validation last 56:
- A5.2 WR 67.86%, PnL +$67.70
- A5.9 WR **73.21%**, PnL **+$70.30**
- 5 actions, 3 rescued, 0 positive->negative
- delta **+$2.60**

Thus the frozen rule improves both chronological periods.

## Eight blocks
A5.9 block PnLs:
- B1 -$13.16
- B2 +$22.13
- B3 +$7.63
- B4 +$18.20
- B5 +$20.61
- B6 +$33.69
- B7 +$4.94
- B8 +$26.22

=> **7/8 blocks positive**.

Incremental A5.8 delta vs A5.2 by block is not uniformly positive:
- B1 +$2.83
- B2 -$4.14
- B3 +$13.07
- B4 0
- B5 0
- B6 +$2.21
- B7 -$5.75
- B8 +$6.14

This matters: the rule improves total robustness but still clips some large runners in individual blocks.

## Year view
- 2024: A5.2 +$3.89 -> A5.9 **+$15.66**, WR 47.17 -> 52.83
- 2025: +$80.15 -> **+$82.36**, WR 69.23 -> 71.15
- 2026 through July: +$28.10 -> **+$28.48**, WR 66.67 -> 73.33

## Leave-one-action-out
Full A5.9 PnL = +$120.27.
Removing any one beneficial rescue still leaves PnL above roughly +$115.27. Therefore uplift is not dependent on one single rescue event.

Two intervention events had large negative deltas because an original large winner was locked small:
- one about -$4.14 delta
- one about -$5.75 delta

Those are the next obvious refinement target.

## Local plateau / frontier
A small neighborhood remains strong:
- d20 0.40 / pull30 / latency60: **WR64.03%, +$120.27**
- d20 0.425 / pull30 / latency60: **WR63.31%, +$125.16**
- d20 0.45 / pull30 / latency60: **WR63.31%, +$125.16**
- d20 0.425–0.45 / pull35 / latency60–75: WR63.31%, about +$123.44

This creates a real frontier rather than a single-point spike:
- **balanced / higher WR:** d20>=0.40 => 64.03% WR, +$120.27
- **money-first:** d20>=0.425–0.45 => 63.31% WR, +$125.16

Looser d20 0.35 can push WR to 65.47% but does not improve validation economics versus A5.2, so it is not selected as the robust champion.

---

# Current research interpretation

The Tuesday edge now looks like a layered state machine:

1. **Temporal prior:** Tuesday 06:00 SELL.
2. **Base geometry:** TP1.35 / SL0.80 / 6h.
3. **A5.2 failure protection:** after +0.50 MFE, protect a narrow price-path failure state.
4. **A5.8/A5.9 fast mean-reversion layer:** for remaining trades, detect severe EMA20 downside overextension followed by unusually fast giveback; arm +0.20 lock.

EMA therefore has useful causal value as a **relative overextension / mean-reversion sensor**, not as a broad entry signal or broad reclaim exit.

# Current provisional balanced champion

**Tuesday 06:00 SELL / TP1.35 / SL0.80 / max6h + A5.2 + A5.9 fastMR**
- 139 trades
- **WR 64.03%**
- **PnL +$120.27**
- **PF 1.638**
- max DD $26.64
- max loss streak 4
- **7/8 positive blocks**

This is materially better than both the static parent and A5.2 on the same 971-day sample, and the frozen rule improves both discovery and validation halves.

Still not production-ready: the incremental FastMR layer acts only 12 times historically, and the whole research path has used the same 971-day dataset for discovery. The rule should remain frozen for true forward/OOS data and/or be tested on an independent analogous temporal cluster before live deployment.
