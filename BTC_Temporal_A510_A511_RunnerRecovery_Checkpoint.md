# BTC Temporal A5.10–A5.11 — Fake Mean-Reversion Runner Recovery

**Date:** 2026-08-16  
**Status:** COMPLETE — runner recovery materially improves A5.9; promising research, not production-ready  
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

## Prior layers
Static parent:
- WR 56.83%
- PnL +$95.73
- PF 1.431
- max DD $31.64
- 6/8 positive blocks

A5.2 price-path protection:
- WR 59.71%
- PnL +$105.90
- PF 1.501
- max DD $26.64
- 6/8 positive blocks

A5.9 FastMR:
- WR 64.03%
- PnL +$120.27
- PF 1.638
- max DD $26.64
- max loss streak 4
- 7/8 positive blocks

A5.9 FastMR rule:
1. Trade has reached +0.50% short MFE.
2. A5.2 does not already act.
3. Hinge close is at least 0.40% below EMA20.
4. Within 60m after hinge, completed 5m close gives back to <=+0.30% short progress.
5. Arm +0.20% profit lock while retaining TP1.35.

---

# A5.10 — Fake Mean-Reversion / Runner Recovery

Question: can we identify FastMR locks that are actually normal pullbacks before bearish continuation, and cancel the lock before it clips a large winner?

Only the 12 historical A5.9 FastMR actions were eligible. The lock remained active during signal formation. If a bar touched the +0.20 lock, the lock had precedence and no retrospective recovery was allowed.

Compact recovery family tested causal completed-5m evidence before lock touch:
- close re-extension thresholds
- two-close re-extension
- EMA7 bearish rejection
- new lower-low continuation

## Best causal runner-recovery pattern

> After A5.9 has armed the +0.20 lock, before that lock is touched, if a COMPLETED 5m candle trades to/above EMA7 but closes back below EMA7 while short close-progress is still >= +0.30%, cancel the +0.20 lock at the next 5m open and restore the original TP1.35 / SL0.80 / 6h runner.

Interpretation:
- FastMR says downside impulse may be exhausted.
- Price then tests EMA7.
- Rejection back below EMA7 while still profitable shows the mean-reversion attempt failed.
- Therefore bearish continuation is re-established and the runner deserves to stay alive.

A5.10 result:
- 139 trades
- 89 wins / 50 losses
- WR 64.03%
- PnL **+$130.33**
- expectancy **+$0.9376/trade**
- PF **1.692**
- max DD $26.64
- max loss streak 4
- 7/8 positive blocks

Incremental vs A5.9:
- +$120.27 -> **+$130.33**
- delta **+$10.06**
- WR unchanged at 64.03% because these were already positive trades; the improvement restores payoff size rather than manufacturing more wins.

Recovery actions: 4 total.
- one large clipped winner in discovery restored: about +$0.25 -> +$4.39 net
- one existing full winner: no economic change
- one large clipped winner in validation restored: about +$0.25 -> +$6.00 net
- one small positive improved: about +$0.25 -> +$0.42 net
- **0 FastMR rescued losses were undone**

---

# A5.11 — Frozen Robustness

The A5.10 EMA7-rejection rule was frozen with +0.30% minimum short progress. No rule re-selection.

## Chronological split
Discovery first 83 Tuesdays:
- A5.9: WR 57.83%, PnL +$49.97
- A5.11: WR 57.83%, PnL **+$54.11**
- delta **+$4.14**
- 2 recovery signals, 1 large runner restored
- 0 rescued losses undone

Validation last 56 Tuesdays:
- A5.9: WR 73.21%, PnL +$70.30
- A5.11: WR 73.21%, PnL **+$76.22**
- delta **+$5.92**
- 2 recovery signals, 1 large runner restored
- 0 rescued losses undone

Thus the same frozen logic improves both chronological halves.

## Eight-block effect
A5.11 block PnLs:
- B1 -$13.16
- B2 +$26.27
- B3 +$7.63
- B4 +$18.20
- B5 +$20.61
- B6 +$33.69
- B7 +$10.69
- B8 +$26.39

=> **7/8 blocks positive**.

Recovery specifically repairs the two A5.9 blocks where large runners had been clipped:
- B2 +$4.14 vs A5.9
- B7 +$5.75 vs A5.9

## Year view
- 2024 A5.9 +$15.66 -> A5.11 **+$19.80**
- 2025 unchanged at +$82.36
- 2026 through July +$28.48 -> **+$34.40**

## Leave-one-recovery-out
Full A5.11 = +$130.33.
- remove the discovery large recovery -> +$126.19
- remove the validation large recovery -> +$124.58
- remove the small recovery -> +$130.16

Therefore the uplift is not dependent on one single recovery event, although the intervention sample is still very small.

## Local threshold plateau
Minimum short progress at EMA7 rejection:
- 0.25% -> +$130.33
- 0.275% -> +$130.33
- 0.30% -> +$130.33
- 0.325% -> +$130.33
- 0.35% -> +$126.19
- 0.375% -> +$126.19
- 0.40% -> +$126.19

Thus the frozen +0.30% threshold sits inside a local plateau (0.25–0.325), not at a single-point spike.

---

# Current layered state machine

1. **Temporal prior** — Tuesday 06:00 WIB SELL.
2. **Base geometry** — TP1.35 / SL0.80 / max6h.
3. **A5.2 price-path protection** — protect narrow giveback state after +0.50 MFE.
4. **A5.9 FastMR** — severe EMA20 downside overextension + rapid giveback => arm +0.20 profit lock.
5. **A5.11 Runner Recovery** — if, before lock touch, price tests EMA7 and is rejected back below it while short progress remains >=+0.30%, cancel lock and restore the full runner.

This gives a coherent role for EMA:
- EMA20 = overextension / mean-reversion-risk reference.
- EMA7 = short-term continuation/rejection reference.

# Current provisional champion

**Tuesday 06:00 SELL / TP1.35 / SL0.80 / max6h + A5.2 + A5.9 FastMR + A5.11 Runner Recovery**
- trades: 139
- wins/losses: 89 / 50
- **WR 64.03%**
- **net PnL +$130.33**
- **expectancy +$0.9376/trade**
- **PF 1.692**
- max DD $26.64
- max loss streak 4
- **7/8 chronological blocks positive**

This is a material improvement over the static parent (+$95.73) and A5.9 (+$120.27) on the same 971-day history.

Still not production-ready. The runner-recovery layer acts only four times historically, with two economically material restorations (one discovery and one validation). The whole research path has reused the same 971-day dataset. Freeze this logic for true forward/OOS validation and/or test the same layered mechanism on an independent analogous temporal engine before live deployment.
