# BTC Temporal A5.4–A5.6 — EMA Failure-State Checkpoint

**Date:** 2026-08-16  
**Status:** COMPLETE — EMA has explanatory/confirmation value, but does not yet dominate A5.2 on all metrics  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation:** 2023-12-02 to 2026-07-30 exclusive (971 days)  
**Tuesday occurrences:** 139  
**Data:** Binance Futures 5m, 100% coverage  
**Parent:** Tuesday 06:00 SELL, TP1.35%, SL0.80%, max hold6h, $500 notional reference, 0.15% round-trip fee

## Existing champions before EMA study

### Static parent
- trades 139
- WR 56.83%
- PnL +$95.73
- PF 1.431
- max DD $31.64
- max loss streak 4
- 6/8 positive chronological blocks

### A5.2 conditional price-path protection
After +0.50% MFE, protect +0.20% only when trigger-close short progress <=+0.35% and cumulative MAE >=0.20%.
- WR **59.71%**
- PnL **+$105.90**
- PF **1.501**
- max DD **$26.64**
- actions 7
- rescued negative->positive 5
- damaged positive->negative 1

---

# A5.4 — EMA failure-state forensic

EMA is used only after the trade has already reached +0.50% short MFE. It is not used to choose Tuesday direction or initial entry.

Tested causal 5m EMA7 / EMA20 features:
- price vs EMA7 / EMA20
- EMA slopes
- EMA7-EMA20 spread/compression
- reclaim
- two-close acceptance

## Key finding: trigger-candle reclaim hypothesis is too early
At the first completed 5m candle that touches +0.50% MFE, almost every case is still below falling EMA7/EMA20.

Full 95 hinge-trades:

Protect-better cases (N21):
- median close distance vs EMA7: **-0.2453%**
- median close distance vs EMA20: **-0.3580%**
- EMA7 1-bar slope: **-0.0817%**
- above EMA7: 0%
- reclaim EMA7: 0%

Runner-better cases (N74):
- median close distance vs EMA7: **-0.1876%**
- median close distance vs EMA20: **-0.2999%**
- EMA7 1-bar slope: **-0.0625%**
- above EMA7: 0%
- reclaim EMA7: 0%

Interpretation: giveback candidates are not already bullish/reclaiming EMA at the hinge. They are typically **more downward-extended from the EMA**, consistent with an exhaustion/mean-reversion interpretation.

No trigger-time EMA rule beat A5.2 across discovery and validation. The only strict cross-period winner remained the original A5.2 frozen price-path rule.

---

# A5.5 — EMA overextension

A compact local family tested EMA distance / downside EMA slope as a gate on A5 failure states.

Best robust EMA-distance candidate:

### FROZEN + at least 0.25% below EMA20
- discovery: +$6.57 delta vs parent, 2 rescued, 0 damaged
- validation: +$1.09 delta, 1 rescued, 0 damaged
- full WR **58.99%**
- full PnL **+$103.40**
- PF **1.480**
- actions 3
- rescued 3
- damaged 0

This is more precise than A5.2 (zero damaged winners) but misses too many valid rescues, so it does **not** beat A5.2's +$105.90 / 59.71%.

Verdict: EMA distance has real descriptive value, but is not yet a superior management gate.

---

# A5.6 — post-hinge EMA confirmation

Instead of requiring an EMA reclaim on the same hinge candle, the trade is allowed to continue after +0.50% MFE. Subsequent COMPLETED 5m bars are monitored. EMA signal exits execute at the next 5m open; parent TP/SL on the signal bar takes precedence.

## Strongest EMA confirmation

Within the already-proven A5 frozen failure context:

> after +0.50% MFE, if there are **2 consecutive completed 5m closes above EMA7**, exit at the next 5m open.

Results vs original static parent:
- trades 139
- WR **57.55%**
- PnL **+$106.32**
- expectancy **+$0.7649/trade**
- PF **1.498**
- max DD **$26.39**
- max loss streak 4
- 6/8 positive blocks
- actions 7
- rescued negative->positive 1
- damaged winner 0
- PnL delta vs static parent **+$10.59**

Chronological split:
- discovery parent +$32.90 -> EMA rule +$39.85 (**+$6.95**)
- validation parent +$62.84 -> EMA rule +$66.47 (**+$3.63**)

Thus the same EMA-confirmation logic improves PnL in both chronological halves.

## Comparison with A5.2

| Metric | Static parent | A5.2 price protect | A5.6 EMA confirm |
|---|---:|---:|---:|
| WR | 56.83% | **59.71%** | 57.55% |
| PnL | +$95.73 | +$105.90 | **+$106.32** |
| Expectancy | $0.6887 | $0.7619 | **$0.7649** |
| PF | 1.431 | **1.501** | 1.498 |
| Max DD | $31.64 | $26.64 | **$26.39** |
| Max loss streak | 4 | 4 | 4 |
| Positive blocks | 6/8 | 6/8 | 6/8 |

A5.6 is the **marginal money/DD champion**, but the gain over A5.2 is tiny (+$0.42 over 971 days) and WR is lower. Therefore this is not enough evidence to replace A5.2 as the balanced research champion.

---

# Important negative control

Using EMA reclaim too broadly after every +0.50% hinge is harmful.

Example ALL_ABOVE7 / reclaim-like exit:
- WR rises to **64.03%**
- but PnL collapses to only **+$9.39**
- 77 EMA exits

This confirms the same lesson as prior A5 work: broad early protection can manufacture high WR by clipping the large runners that create expectancy.

EMA only adds value when conditioned on a narrower, already-proven failure state.

---

# Verdict

**Yes, the Tuesday champion has a relationship with EMA, but the useful relationship is specific:**

1. At the +0.50% hinge, eventual givebacks tend to be more overextended below EMA7/EMA20, not already reclaiming them.
2. Trigger-time EMA reclaim is therefore the wrong causal timing.
3. EMA distance improves precision but misses too many rescues.
4. A later **two-close acceptance above EMA7**, conditioned on the A5 failure state, is a useful continuation-failure confirmation and slightly improves net PnL / drawdown.
5. EMA reclaim used globally raises WR but destroys expectancy.

Current interpretation:

`Tuesday temporal SELL -> reaches +0.50% -> evaluate price-path weakness -> EMA7 two-close acceptance can confirm giveback`

Current balanced champion remains **A5.2** because it has materially higher WR (59.71%) and essentially identical PnL/PF to A5.6. A5.6 is retained as the marginal money/DD alternative.

Neither rule is production-ready; the intervention count is still small and should be frozen for forward/OOS validation and/or tested on an analogous independent temporal cluster such as Friday BUY.
