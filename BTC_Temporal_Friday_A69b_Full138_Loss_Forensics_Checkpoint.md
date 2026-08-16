# BTC Temporal Friday15 — A6.9b Full 138-Trade Loss Forensics

**Date:** 2026-08-17 WIB  
**Status:** FULL-PARENT LOSS FORENSICS — NO FILTER PROMOTION / NO LIVE CHANGE  
**Symbol:** BTCUSDT  
**Entry:** every Friday exact 15:00 WIB BUY  
**Parent execution:** TP 2.0%, SL 0.7%, max hold 360m, fee 0.15% roundtrip, $500 fixed notional  
**Sample:** 138 Friday occurrences, first 82 discovery / last 56 validation  
**Live BBC:** untouched

---

## 1. Full parent population

- 138 trades
- 66 net winners
- 72 net losers
- executable WR **47.83%**
- parent net PnL **+$64.630**
- discovery: 82 trades, WR54.88%, +$99.194
- validation: 56 trades, WR37.50%, -$34.563

This checkpoint analyzes **all 72 losses from the full 138-trade parent**, not the later 63-trade EMA pullback subset.

---

## 2. Mutually-exclusive loss taxonomy

| Family | Definition by 6h MFE | Full | Discovery | Validation |
|---|---|---:|---:|---:|
| A — wrong-way | MFE < +0.30% | **26** | 8 | **18** |
| B — weak pop | +0.30% <= MFE < +0.50% | **14** | 9 | 5 |
| C — giveback | +0.50% <= MFE < +1.00% | **24** | 15 | 9 |
| D — deep giveback | MFE >= +1.00% | **8** | 5 | 3 |

Total = 72 losses.

Shares of all losses:
- A wrong-way: **36.1%**
- B weak-pop: **19.4%**
- C giveback: **33.3%**
- D deep giveback: **11.1%**

Therefore:
- **46/72 = 63.9%** of losses reached at least +0.30% MFE.
- **32/72 = 44.4%** reached at least +0.50% MFE.
- 14/72 reached at least +0.80%.
- 8/72 reached at least +1.00%.
- 2/72 reached at least +1.50%.

---

## 3. Major regime shift inside Friday losses

The taxonomy distribution changes materially across the chronological split.

### Discovery first82
37 losses total:
- A wrong-way: 8 = **21.6%**
- B weak-pop: 9 = 24.3%
- C giveback: 15 = **40.5%**
- D deep giveback: 5 = 13.5%

### Validation last56
35 losses total:
- A wrong-way: 18 = **51.4%**
- B weak-pop: 5 = 14.3%
- C giveback: 9 = 25.7%
- D deep giveback: 3 = 8.6%

Interpretation:

> The old Friday engine often lost by first moving correctly and then giving back. In the later period, the dominant failure mode became **immediate wrong-way / no rebound**.

This is a plausible structural explanation for the parent collapsing from +$99.194 discovery to -$34.563 validation despite the long-run Friday BUY directional tendency.

---

## 4. Winner vs wrong-way path separation

### Full medians

At 15m after entry:
- WIN progress **+0.1243%**
- A wrong-way **-0.0810%**
- WIN taker flow +0.0264
- A taker flow -0.0154

At 30m:
- WIN progress **+0.1963%**
- A **-0.1739%**
- WIN MFE +0.3206%
- A MFE +0.0926%

At 60m:
- WIN progress **+0.2228%**
- A **-0.3230%**
- WIN MFE +0.4586%
- A MFE +0.0926%
- WIN MAE 0.1264%
- A MAE **0.4383%**
- WIN taker +0.0095
- A taker **-0.0230**

Thus the wrong-way family becomes visibly different very early, especially by 30–60m.

### Validation medians

At 15m:
- WIN progress **+0.1198%**
- A **-0.0543%**

At 30m:
- WIN **+0.2569%**
- A **-0.1870%**

At 60m:
- WIN **+0.3115%**
- A **-0.1957%**
- WIN MFE +0.5065%
- A MFE +0.0985%
- WIN taker +0.0066
- A taker -0.0262

The early separation remains present in the later period.

---

## 5. Giveback families

### C — +0.50 to +1.00 MFE, eventual loss
24 trades.

Full medians:
- MFE **+0.6991%**
- MAE 0.9141%
- peak time ~192.5m
- 15m progress +0.1373%
- 60m progress +0.1230%
- 120m progress +0.1834%
- 240m progress turns roughly flat/slightly negative: **-0.0211%**
- 360m progress **-0.3282%**

This family initially looks more like a valid BUY than a wrong-way trade, then loses momentum between roughly 2h and 4h.

### D — >= +1.00 MFE, eventual loss
8 trades.

Full medians:
- MFE **+1.2686%**
- MAE 1.0049%
- peak time ~270m

These are true deep-runner givebacks. They are much smaller in count but represent the clearest profit-preservation opportunity.

---

## 6. SL versus timeout diagnosis

Full parent exits:
- TP: 19
- SL: 51
- timeout: 68

Among the 72 net losses:
- **51 hit SL**
- **21 timeout negative**

So unlike Saturday, Friday loss is mostly a genuine stop-hit problem rather than merely negative timeout drift.

### What happens after SL inside the original 6h horizon?

Among 51 SL losses:
- 18 later recover enough to trade at least +0.15% above original entry (fee-level gross recovery)
- 11 later reach +0.50%
- 3 later reach +1.00%
- only **2 later reach the original +2.00% TP**

Chronological split:
- discovery: 25 SL losses; 2 later reach +2.0%
- validation: 26 SL losses; **0** later reach +2.0%

Therefore:

> The majority of Friday SL losses are not simply “SL too tight then price eventually hits TP.” Widening SL is not supported as the primary solution, especially in validation.

---

## 7. Current mechanistic interpretation

There are at least two distinct Friday problems:

### Problem 1 — later-regime wrong-way failure
- 26 full-sample cases, but concentrated heavily in validation (18/35 validation losses).
- fails to generate meaningful MFE.
- winner/loss separation appears by 15m and becomes large by 30–60m.
- this is primarily a **thesis-validation / dynamic state / possible direction-switch** problem.

### Problem 2 — valid rebound that later gives back
- C+D = **32 losses**, 44.4% of all losses.
- these trades first prove Friday BUY was directionally correct.
- this is a **runner/profit-management** problem, not an entry-direction problem.

One universal Friday filter is therefore unlikely to be ideal. A higher-coverage engine should instead consider different management after observing the causal post-entry path.

---

## 8. Research implication

Do not optimize another pre-entry filter yet.

The next constructive sequence should keep **all 138 Friday occurrences** as the parent population and test:

1. an early causal thesis-state at 15/30/60m that distinguishes wrong-way failure from delayed winners **without simply skipping Friday ex ante**;
2. separate profit-preservation logic for the 32 C+D giveback losses;
3. only then consider dynamic BUY/HOLD/SELL behavior for wrong-way states.

Any intervention must be evaluated on discovery and validation separately, with fee counted and no current-candle look-ahead.
