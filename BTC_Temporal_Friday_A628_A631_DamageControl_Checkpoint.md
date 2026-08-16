# BTC Temporal Friday15 — A6.28–A6.31 Damage Control Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** PROVISIONAL BALANCED UPGRADE — NOT LIVE / NOT FINAL OOS PROVEN  
**Symbol:** BTCUSDT  
**Entry:** every Friday exact 15:00 WIB BUY  
**Sample:** 138 Fridays; first82 discovery / last56 validation  
**Live BBC:** untouched

## Reference entering this pass — A6.22 Balanced

- 138/138 Friday entries
- WR 60.87%
- PnL +$128.989
- expectancy +$0.9347/Friday
- PF 1.637
- max DD $51.993
- max loss streak 4
- discovery: WR67.07%, +$137.053
- validation: WR51.79%, -$8.065

Frozen management before this pass:
- parent BUY TP2.0 / SL0.7 / max6h
- frozen failed-thesis detector: at60m MFE<+0.3, progress<0, taker<0, below EMA20, EMA20 slope down; confirm at120m still MFE<+0.3 and progress<0
- if BUY already stopped before120 and failure remains confirmed: sequential SHORT TP1.5/SL0.5
- if BUY still open at120: existing balanced FLIP logic TP1.3/SL0.7
- selective A6.15 distribution protection remains unchanged

## A6.28 — direct early CUT rejected

Tested causal direct CUT at 15/30/60/90m with compact no-proof / negative-progress / taker / EMA20 failure states. All candidates chosen by discovery engine PnL were worse than A6.22.

Best discovery candidate was 90m no-proof + below EMA20:
- discovery delta -$15.177
- validation delta +$6.253
- full delta -$8.924
- full WR fell to 55.07%

Interpretation: many delayed Friday winners look weak before the rebound. A single early-failure snapshot is not sufficient for direct liquidation.

## A6.29 — two-stage CUT partially works, but not balanced

Added warning -> recovery window -> confirmation. Best discovery-eligible rule:
- warning at90m: MFE<+0.3, progress<0, below EMA20
- confirm at120m: still MFE<+0.3 and progress<0
- CUT at actual120m open

Results:
- full PnL +$135.084 vs A6.22 +$128.989
- PF 1.711
- discovery +$140.796, delta +$3.743
- validation -$5.713, delta +$2.352
- but WR fell 60.87% -> 57.25%
- max loss streak worsened 4 -> 8

Therefore A6.29 is a PnL-first alternate, not a balanced promotion.

## A6.30 — conditional tight stop succeeds

Instead of fixed-time CUT, after the already-frozen 60m FULL failure warning:
- do NOT close immediately;
- tighten the original BUY protective stop from -0.70% to **-0.50%**;
- this tighter stop is active from the actual60m open through just before the120m decision;
- if the tighter stop fires and the frozen failure state is still confirmed at120m, the existing post-stop sequential SHORT TP1.5/SL0.5 remains allowed;
- if the trade survives, A6.22 management continues unchanged.

The 0.50 cap was selected using first82 discovery PnL only from the compact candidate set {60m FULL or90m D20 warning} x {0.50,0.60 stop cap}.

### A6.30 results

Full:
- N 138
- WR **60.87% unchanged**
- PnL **+$137.132**
- expectancy **+$0.9937/Friday**
- PF **1.686**
- max DD **$49.350**
- max loss streak **4**
- delta vs A6.22 **+$8.143**

Discovery:
- WR67.07% unchanged
- +$138.580
- delta **+$1.526**
- only 2 actions: both original losers

Validation:
- WR51.79% unchanged
- **-$1.448** vs -$8.065
- delta **+$6.617**
- 9 actions: 8 original losers / 1 original winner

Full action attribution:
- 11 actions
- 10 original losers
- 1 original winner
- **90.91% original-loss precision**
- 9/10 touched original losers became less negative vs A6.22
- 0 baseline positive occurrences became negative
- loss-side uplift +$7.730
- winner-side delta +$0.413

Year deltas vs A6.22:
- 2024 +$1.526
- 2025 +$0.643
- 2026 through Jul +$5.974

## A6.31 — local robustness

Reference stays A6.30 cap=0.50. Local cap perturbation is diagnostic only; do not post-hoc replace canonical.

| Conditional stop cap | Full PnL | Discovery delta | Validation PnL | Validation delta | WR |
|---|---:|---:|---:|---:|---:|
| 0.45% | +$138.330 | +$0.753 | +$0.523 | +$8.588 | 60.87% |
| **0.50% reference** | **+$137.132** | **+$1.526** | **-$1.448** | **+$6.617** | **60.87%** |
| 0.55% | +$134.500 | +$1.276 | -$3.829 | +$4.236 | 60.87% |
| 0.60% | +$132.989 | +$1.000 | -$5.065 | +$3.000 | 60.87% |
| 0.65% | +$130.989 | +$0.500 | -$6.565 | +$1.500 | 60.87% |

Every tested cap from 0.45–0.65 improves full, discovery, and validation PnL versus A6.22 while preserving WR. This supports the mechanism as a plateau rather than a single exact stop value.

Important: 0.45 makes validation slightly positive, but this was observed only during robustness. **Do not promote 0.45 on this sample.** The canonical research reference remains 0.50.

### Robustness details for cap0.50

- leave-one-action-out total PnL range: **+$136.132 to +$137.457**; every case remains above A6.22 +$128.989
- chronological blocks: 5 positive delta, 3 zero, **0 negative-delta blocks**
- extra cost stress applied to each of 11 tight-stop actions:
  - +0.02%: +$136.032
  - +0.05%: +$134.382
  - +0.10%: +$131.632
  - +0.15%: +$128.882 (approximately baseline; the uplift is largely consumed at this extreme action-only cost)

## Current Friday balanced research reference

### A6.30 / A6.31 reference

Every Friday15 still enters. No pre-entry filtering.

1. BUY Friday15, TP2.0 / SL0.7 / max6h.
2. At60m, using completed5m data only, detect FULL failure warning:
   - cumulative MFE < +0.30%
   - progress < 0
   - taker-flow < 0
   - price below EMA20
   - EMA20 15m slope < 0
3. If warning true and BUY is still alive, tighten first-leg SL to **-0.50%** until the120m decision.
4. At120m, use the already-frozen failed-thesis confirmation and existing A6.22 management:
   - post-stop confirmed failure -> sequential SHORT TP1.5 / SL0.5;
   - still-open confirmed failure -> existing balanced flip logic;
   - otherwise normal parent / distribution logic.

Current metrics:
- N138
- WR **60.87%**
- PnL **+$137.132**
- expectancy **+$0.9937/Friday**
- PF **1.686**
- max DD **$49.350**
- LS4
- validation **-$1.448**, very near break-even

## Cautions

- The mechanism is economically and locally robust, but the reference cap0.50 has only 2 discovery actions and 9 validation actions. Low discovery event count is the key remaining evidence weakness.
- The local cap plateau materially strengthens confidence but does not make the 56 validation cases a new training set.
- Do not switch to cap0.45 merely because validation becomes +$0.523.
- No live implementation yet.
- Correct next proof is fresh unseen Fridays or transfer of the frozen damage-control mechanism to another comparable temporal BUY setup, rather than more threshold squeezing on the same 138 Friday sample.
