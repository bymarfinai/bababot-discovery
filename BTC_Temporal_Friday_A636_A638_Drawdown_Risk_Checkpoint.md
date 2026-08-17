# BTC Temporal Friday15 — A6.36 to A6.38 Drawdown/Risk Checkpoint

**Date:** 2026-08-17 WIB  
**Live BBC:** untouched  
**Reference engine:** A6.33 EMA early-warning provisional champion  
**Reference metrics:** N138, WR60.87%, PnL +$141.025, PF1.720, max DD $46.318, max loss streak 4.

## A6.36 — Max drawdown forensics

The A6.33 max drawdown is a long regime drawdown, not a simple loss streak:
- peak: 2025-05-02, equity $144.073
- trough: 2026-01-30, equity $97.754
- max DD: $46.318
- 39 Friday occurrences from peak to trough
- not recovered within the available sample.

Layer contribution during the peak-to-trough descent:
- PARENT: 26 occurrences, net -$12.505
- DISTRIBUTION: 3, net +$0.319
- WRONGWAY_STILLOPEN: 2, net +$2.367
- DAMAGE_FULL60: 1, net -$6.500
- WRONGWAY_POSTSTOP: 1, net -$7.500
- DAMAGE_EMA45: 6, net -$22.500

Largest individual hits include post-stop/damage-control double-loss occurrences around -$6.50 to -$7.50. Three -$6.50 damage-control+wrongway events occurred in Jan 2026.

Full-sample layer stats show PARENT remains strongly profitable (+$170.396, PF2.518), while difficult wrong-way/damage subsets naturally remain negative in absolute PnL. The purpose of management is loss reduction, not standalone profitability.

## A6.37 — Broad drawdown-aware sizing

All 138 entries remain. Risk state is based only on completed prior normalized A6.33 shadow-equity outcomes.

Key variants:

| Policy | Full PnL | Full MDD | WR | Comment |
|---|---:|---:|---:|---|
| A6.33 BASE | +141.025 | 46.318 | 60.87% | reference |
| DD>=2R, whole occurrence 75% | +130.391 | 37.993 | 60.87% | meaningful DD cut but ~7.5% PnL cost |
| DD>=3R, whole occurrence 75% | +134.151 | 39.371 | 60.87% | moderate trade-off |
| DD>=2R, whole occurrence 50% | +119.757 | 29.668 | 60.87% | large DD cut, excessive PnL cost |
| DD>=2R, second leg 75% | +137.387 | 45.198 | 60.87% | small DD benefit |
| after 2 losses, whole occurrence 75% | +139.258 | 44.632 | 60.87% | discovery-selected, but weak full DD improvement |

Discovery-only selection chose `LOSS2_OCC075`, because discovery PnL stayed >=95% of baseline and discovery MDD was lowest. However, validation PnL moved from +$1.553 baseline to -$0.574 and full MDD only improved from $46.318 to $44.632. **Do not promote over A6.33.**

## A6.38 — Targeted post-stop second-leg risk

Mechanism: only resize the sequential SHORT when A6.33 damage-control already stopped the BUY early and wrong-way confirmation still triggers. Normal Friday trades and still-open cases remain unchanged.

Predeclared candidate: when prior shadow DD >=2R, size that sequential SHORT at 50%.
- Full: WR60.87%, +$135.884, PF1.712, MDD $43.193
- Discovery: +$137.956, MDD $21.691 (worse than baseline discovery MDD $20.176)
- Validation: -$2.072, MDD $38.592
- Verdict: reject as canonical.

A notable *forward hypothesis* appeared in the compact variant set:
`after 2 consecutive Friday losses -> only damage-control sequential SHORT at 50% size`.
- Full: WR60.87%, +$140.900, PF1.731, MDD $43.068
- Validation: +$1.428, MDD $38.467
- Full PnL cost vs A6.33: only -$0.125
- Full MDD improvement: $3.250 (~7.0%)

However, this policy had **zero actions in the first82 discovery sample** and all three actions occurred later. Therefore it cannot be claimed as discovery-validated or promoted based on current data. Keep it only as an OOS/forward-test hypothesis.

## Current verdict

**A6.33 remains the provisional Friday15 champion.**

Best scientifically defensible conclusion:
1. Max DD is driven by a prolonged 2025-2026 weak regime, not merely a four-loss streak.
2. Blanket risk reduction can lower DD to ~$30-40, but costs too much PnL.
3. Targeting post-stop double-losses is directionally better, but current discovery evidence is insufficient.
4. Do not silently adopt the attractive LOSS2 targeted overlay from full/validation results.
5. Forward/OOS test the hypothesis: after two completed negative Friday occurrences, keep the next Friday15 BUY full-size but halve only a damage-control-triggered sequential SHORT. Reset after a positive Friday occurrence.
6. Live remains untouched.
