# BTC Temporal Friday15 — A6.17–A6.20 Parity-Correct Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** PROVISIONAL FULL-COVERAGE RESEARCH CANDIDATE — NOT LIVE / NOT FINAL  
**Symbol:** BTCUSDT  
**Entry:** every Friday exact 15:00 WIB BUY  
**Parent:** TP2.0%, SL0.7%, max6h, fee0.15%, $500 notional  
**Sample:** 138 Fridays, first82 discovery / last56 validation  
**Live BBC:** untouched

## Critical correction to prior A6.12/A6.15 checkpoint

A6.17 discovered a live-parity bookkeeping defect in the old A6.12 wrong-way action. Of 27 120m confirmed-failure cases, **15 had already hit the original BUY exit before the 120m decision**. The old action replaced the realized BUY result with synthetic long PnL at the 120m open, which is not executable.

Therefore the old A6.12 metrics (WR52.17 / +$77.878) and old A6.12+A6.15 combined metrics (WR56.52 / +$93.189) are **superseded as engine-level results**. The A6.15 distribution mechanism itself remains valid because it is applied only to non-wrongway trades and is re-evaluated here on top of the parity-correct wrong-way baseline.

## A6.17b parity repair

Failure detector stays frozen:
- at 60m: MFE<+0.3%, progress<0, taker<0, below EMA20, EMA20 15m slope<0;
- at 120m: still MFE<+0.3% and progress<0.

Execution repair:
- if original BUY is still open at 120m: close at actual 120m open, then open SHORT;
- if original BUY already exited before 120m: preserve realized parent PnL exactly and optionally open a new sequential SHORT at 120m;
- original six-hour horizon remains the expiry.

Counts:
- confirmed failure: 27
- already exited before120: 15
- still open at120: 12

With sequential SHORT TP1.0/SL0.7:
- WR53.62%
- PnL +$91.344
- PF1.412
- discovery +$17.988 vs parent
- validation +$8.725 vs parent

No-reentry was inferior (WR50.0, +$68.677; validation -$35.755).

## A6.17 atlas / A6.18 router

The atlas showed that blindly shorting an already deeply stretched decline can chase exhaustion. A compact 120m EMA-distance router improved validation economics in some variants, but reduced headline WR versus parity-correct all-short handling and had discovery ties/threshold ambiguity. It is **not promoted**.

Useful mechanism only:
> failed BUY does not imply unlimited bearish continuation; downside stretch matters.

## A6.19 sequential SHORT geometry

Important parity insight: a prior BUY SL is approximately -$4.25 net. A new SHORT TP1.0 after fee also yields roughly +$4.25 net, so a successful sequential TP1.0 often only returns the whole Friday occurrence to ~$0 rather than a positive win.

With detector and SL0.7 frozen, compact TP set was tested using discovery PnL for selection:

| SHORT TP | Full WR | Full PnL | Discovery PnL | Validation PnL | Validation WR |
|---|---:|---:|---:|---:|---:|
| 1.0% | 53.62% | +$91.344 | +$117.182 | -$25.838 | 44.64% |
| 1.1% | **57.25%** | +$96.346 | +$118.184 | -$21.838 | **50.00%** |
| 1.2% | 56.52% | +$100.627 | +$118.465 | -$17.838 | 50.00% |
| **1.3%** | 56.52% | **+$101.094** | **+$118.884** | **-$17.790** | 50.00% |

TP1.3 was selected canonically because it had the best discovery PnL before validation. TP1.1 remains an explicit WR-first alternate.

A6.19 TP1.3 by year:
- 2024: +$90.317
- 2025: -$4.632
- 2026 through Jul: +$9.228
- 6/8 chronological blocks had positive delta vs original parent.

## A6.20 parity-correct combined engine

Two disjoint management layers:

### Wrong-way layer
- all original Friday BUY entries remain;
- frozen 60m +120m failed-thesis detector;
- parity-correct sequential SHORT at120;
- canonical SHORT TP1.3%, SL0.7%, original horizon expiry.

### Distribution giveback layer — only when wrong-way layer did not fire
- original BUY reaches +0.5% while still open;
- within60m a completed5m close gives back to <=+0.3%;
- taker flow <= -0.04;
- completed close still above EMA20;
- next5m open arm +0.20% profit lock while retaining TP2.0.

All state inputs use completed candles only.

### Canonical A6.20 — TP1.3 SHORT

- original Friday BUY occurrences: **138 / 138**
- WR **60.87%**
- PnL **+$116.406**
- expectancy **+$0.8435 / Friday**
- PF **1.565**
- max DD **$55.576**
- max loss streak **4**
- wrong-way actions: 27
- of those, prior BUY already exited in 15 cases
- distribution actions: 13
- management actions total: 40
- **20 original loss -> positive** across the two management layers
- **2 original winner -> loss**
- 4 winner clipped but remain positive

Versus original parent:
- WR 47.83% -> **60.87%**
- PnL +$64.630 -> **+$116.406**
- PF1.266 -> **1.565**
- loss streak8 -> **4**
- delta PnL **+$51.775**

Discovery first82:
- WR **67.07%**
- PnL **+$133.053**
- PF2.439
- delta +$33.860 vs parent
- 10 loss->positive, 0 winner->loss.

Validation last56:
- WR **51.79%**
- PnL **-$16.648**
- PF0.853
- delta **+$17.916** vs parent validation -$34.563
- 10 loss->positive, 2 winner->loss.

The validation engine remains net-negative, so this is not a production champion despite the large improvement.

### WR-first alternate — TP1.1 SHORT

Same engine, only sequential SHORT target is 1.1%:
- WR **61.59%**
- PnL **+$111.658**
- expectancy +$0.8091
- PF1.545
- DD$53.624
- discovery WR68.29%, +$132.354
- validation WR51.79%, -$20.696

This has the highest current full-sample WR, but it was not selected as canonical because TP1.3 wins the predeclared discovery-PnL objective.

## Chronological robustness — canonical A6.20

7/8 blocks have positive delta versus original parent.

By year:
- 2023: +$6.181 unchanged
- 2024: **+$92.991**, WR67.31%, delta +$23.255
- 2025: **+$6.864**, WR53.85%, delta +$21.048; parent was -$14.185
- 2026 through Jul: **+$10.370**, WR60.00%, delta +$7.473

Thus combined management turns 2025 positive and improves every active calendar year.

Extra hypothetical execution cost applied once to each of the 40 management events:
- +0.02%: +$112.406
- +0.05%: +$106.406
- +0.10%: +$96.406
- +0.15%: +$86.406

PnL remains positive under these stresses, although some small positive outcomes become net-negative and headline WR declines.

## Current Friday status

### Original full-coverage parent
- 138 entries
- WR47.83%
- +$64.63

### Current parity-correct canonical research candidate
- **138 original entries**
- **WR60.87%**
- **+$116.406**
- **PF1.565**
- **loss streak4**
- **7/8 positive-delta blocks**

### Explicit WR-first alternate
- 138 entries
- **WR61.59%**
- +$111.658

## Cautions / locks

- This is a **PROVISIONAL research candidate, not live**.
- Overall validation PnL remains negative even though it improves materially.
- Do not report the older A6.12/A6.15 engine-level metrics as parity-correct; they are superseded by this checkpoint.
- Do not silently optimize more thresholds on the same BTC Friday sample and call them OOS.
- Any further Friday improvement should focus on a genuinely new mechanism, transfer test, or walk-forward regime logic rather than more local threshold squeezing.
- Live implementation, if later approved, must preserve realized exits, treat post-stop SHORT as a new sequential trade, use actual exchange fills, completed5m state only, exchange-side protection, and one-position/reconciliation safeguards.
