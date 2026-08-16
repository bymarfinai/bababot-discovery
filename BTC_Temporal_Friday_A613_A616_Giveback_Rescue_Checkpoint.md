# BTC Temporal Friday15 — A6.13–A6.16 Giveback Rescue Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** PROVISIONAL FULL-COVERAGE RESEARCH CHAMPION — NOT LIVE / NOT FINAL  
**Symbol:** BTCUSDT  
**Parent entry:** every Friday exact 15:00 WIB BUY  
**Parent geometry:** TP 2.0%, SL 0.7%, max hold 6h, fee 0.15%, $500 fixed notional  
**Sample:** 138 Fridays, first 82 discovery / last 56 validation  
**Live BBC:** untouched

## 1. Starting points

Original full Friday parent:
- N 138
- WR 47.83%
- PnL +$64.630
- PF 1.266
- max DD $56.530
- max loss streak 8

A6.12 provisional wrong-way layer:
- all 138 still enter
- 60m initial failure + 120m persistent no-+0.3/negative confirmation
- confirmed failure flips SHORT TP1.0 / SL0.7 for remaining original horizon
- WR 52.17%
- PnL +$77.878
- PF 1.325
- max loss streak 4
- discovery delta +$8.812 vs parent
- validation delta +$4.435 vs parent

## 2. A6.13 executable-capacity correction

The earlier loss taxonomy found 32 C+D losses whose full 6h path eventually reached >=+0.5% MFE. That was an oracle/path statistic, not automatically executable.

A6.13 required the +0.5% hinge to occur **while the original BUY was still open**. If +0.5% and SL occurred on the same 5m candle, adverse-first policy treats the SL as occurring first, so the hinge is not actionable. Trades already taken over by the A6.12 wrong-way flip are also excluded from the long giveback layer.

Executable hinge capacity after those restrictions:
- eligible total: 82
- eligible original winners: 61
- eligible original losses: **21**
- eligible C losses: 18
- eligible D losses: 3

Therefore the live-actionable giveback ceiling is materially smaller than the earlier 32-loss hindsight count.

## 3. Broad giveback protection rejected

Broad event studied:
- BUY first reaches +0.5% while still open
- within 60m, a completed 5m close falls back to <=+0.3%
- next 5m open decision
- arm +0.2% profit lock; TP2.0 remains alive

This could raise headline WR sharply but destroyed expectancy by clipping too many healthy runners.

Example broad result on top of A6.12:
- WR 60.87%
- PnL only +$38.315
- 16 loss→win but 20 winners clipped and 4 winners became losses

Verdict: broad giveback protection is rejected.

## 4. A6.14 runner-vs-loss atlas

For the broad +0.5 -> <=+0.3 within60m event:

Full medians:
- eventual WIN taker flow: -0.0188
- eventual LOSS taker flow: **-0.0508**
- WIN distance above EMA20: +0.0131%
- LOSS distance above EMA20: **+0.0768%**
- WIN EMA20 short slope: +0.0362%
- LOSS: +0.0518%

Validation preserved the same direction:
- WIN taker -0.0167 vs LOSS -0.0281
- WIN d20 -0.0043% vs LOSS +0.0718%

Interpretation: damaging givebacks look less like ordinary pullbacks and more like **aggressive seller flow appearing while price is still elevated above EMA20** — a distribution-like state.

Simple cumulative-MFE caps (.70/.80/1.00) were insufficient; they raised WR but still reduced PnL. Rejected as standalone discriminator.

## 5. A6.15 selective distribution giveback candidate

Fixed sequence:
1. all 138 Fridays still enter BUY at 15:00 WIB;
2. A6.12 wrong-way logic has priority;
3. otherwise original BUY must reach +0.5% while still open;
4. within 60m, completed 5m close gives back to <=+0.3%;
5. require strong seller taker-flow **<= -0.04**;
6. require that completed close is still **above EMA20**;
7. at next 5m open, arm a **+0.20% profit lock**; TP2.0 remains alive;
8. if price already passed the lock at the decision open, exit at actual open; same-bar TP+lock resolves lock-first.

All inputs are completed-candle causal; no current-candle look-ahead.

### Result on top of A6.12

- N **138**
- WR **56.52%**
- PnL **+$93.189**
- expectancy **+$0.6753/trade**
- PF **1.418**
- max DD **$55.348**
- max loss streak **4**
- distribution actions: 13
- **6 original loss → positive**
- **0 original winner → loss**
- 4 original winners clipped but remain positive

Improvement vs A6.12:
- WR +4.35pp
- PnL **+$15.312**

Improvement vs original parent:
- WR 47.83% → **56.52%**
- PnL +$64.630 → **+$93.189**
- PF 1.266 → **1.418**
- loss streak 8 → **4**

Chronological contribution of the A6.15 layer vs A6.12:
- discovery: **+$14.170**
- validation: **+$1.142**

Important: the *overall* validation engine remains negative (-$28.986), although this layer improves validation relative to A6.12 (-$30.128). This is why the strategy is not yet a production champion.

## 6. Year behavior

With A6.12 + A6.15 combined:

- 2023: +$6.181, unchanged
- 2024: **+$82.113**, delta +$2.674 vs A6.12
- 2025: **+$4.697**, delta +$11.495; A6.12 alone was -$6.799
- 2026 through Jul: **+$0.199**, delta +$1.142; A6.12 alone was -$0.943

Thus the selective giveback layer improved every year in which it acted.

## 7. A6.16 local robustness

Taker threshold plateau, with d20>0 and +0.20 lock fixed:

| Taker threshold | Actions | WR | PnL | Delta vs A6.12 | Discovery delta | Validation delta |
|---|---:|---:|---:|---:|---:|---:|
| -0.035 | 15 | 56.52% | +$81.768 | +$3.890 | +$2.748 | +$1.142 |
| **-0.040** | **13** | **56.52%** | **+$93.189** | **+$15.312** | **+$14.170** | **+$1.142** |
| -0.045 | 12 | 55.80% | +$88.727 | +$10.849 | +$9.707 | +$1.142 |
| -0.050 | 12 | 55.80% | +$88.727 | +$10.849 | +$9.707 | +$1.142 |

Conclusion: -0.04 is best in this local set but is **not an isolated profitable spike**. Nearby stricter/looser values remain positive versus A6.12 in both chronological splits.

Leave-one-intervention-out for canonical -0.04:
- minimum total PnL **+$88.689**
- maximum +$94.514
- all remain above A6.12 +$77.878

Extra execution-cost stress on the 13 distribution actions only:
- +0.02% extra: +$91.889
- +0.05%: +$89.939
- +0.10%: +$86.689
- +0.15%: +$83.439

PnL remains above A6.12 even at +0.15% extra action cost, though WR classification drops under high extra cost because some small protected positives become net-negative after the hypothetical surcharge.

## 8. Current Friday ranking

### Full-coverage parent
Every Friday15 BUY, TP2/SL0.7/6h:
- 138 trades
- WR47.83%
- +$64.63

### Provisional full-coverage dynamic champion
Parent + A6.12 wrong-way state + A6.15 selective distribution giveback:
- **138 trades**
- **WR56.52%**
- **+$93.189**
- **PF1.418**
- **loss streak4**

This is currently the best high-coverage Friday engine found without using a pre-entry filter to remove half the Fridays.

## 9. Status / caution

- **PROVISIONAL research champion only.**
- Do not silently retune this same BTC Friday sample further and call the result OOS.
- Overall validation remains negative despite both dynamic layers improving it.
- The A6.15 validation contribution comes from only one action, so transfer/OOS evidence is still needed.
- Do not deploy to live BBC yet.
- Live implementation, if later approved, must use actual exchange fills and completed 5m state only.
