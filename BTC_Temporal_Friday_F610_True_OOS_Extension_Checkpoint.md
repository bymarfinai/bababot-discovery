# BTC Temporal Friday F6.10 — Frozen True-OOS Extension

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — TRUE-OOS OBSERVATION ONLY; FROZEN FAILURE BRANCHES NOT YET EXERCISED  
**Research only:** live BBC untouched.

## Frozen OOS protocol

- Last Friday scored in the same-sample research: **2026-07-24**.
- True-OOS entries scored: Friday 15:00 WIB on **2026-07-31, 2026-08-07, 2026-08-14**.
- Exact frozen F6.9 +10m rule replayed with zero changes.
- If F6.9 did not act, exact frozen F6.5 +60m rule was evaluated with zero changes.
- Historical candles were used only for indicator warmup; only the three OOS Fridays above were scored.

## Aggregate true-OOS result

- N: **3**
- Parent: **1W / 2L**, PnL **-$2.312**
- F6.9 EARLY10 actions: **0**
- F6.5 later actions: **0**
- Layered PnL: **-$2.312**
- Layered delta: **$0.000**

## Trade-by-trade

### 2026-07-31
- Parent: **-$4.250**, SL
- MFE **+0.114%**, MAE **-0.749%**
- F6.9 EARLY10: **NO**
- F6.5: **NO**
- First 5m was not red; second 5m traded back through entry.

### 2026-08-07
- Parent: **+$4.663**, TIMEOUT
- MFE **+1.663%**, MAE **-0.031%**
- F6.9 EARLY10: **NO**
- F6.5: **NO**
- First 5m was not red; second 5m traded back through entry.

### 2026-08-14
- Parent: **-$2.725**, TIMEOUT
- MFE **+0.137%**, MAE **-0.529%**
- F6.9 EARLY10: **NO**
- F6.5: **NO**
- First 5m was not red; second 5m traded back through entry.

## Critical interpretation

This OOS observation does **not** test the quality of the frozen early-sink or +60m true-failure actions because neither branch triggered on any of the three unseen Fridays.

The most important fact is structural:

> all three unseen Fridays failed the very first prerequisite of the frozen EARLY10 state — the first 5m candle was not red — and all three had a second 5m high that reclaimed/traded through entry.

Therefore these are not historical analogues of the F6.6 immediate-sink cohort.

The parent itself is currently slightly negative OOS at -$2.312 over N=3, but with one positive Friday and only three observations this is not sufficient to redesign the entry or management layers.

## Frozen research status

Same-sample candidate remains:
- F6.9 EARLY10 standalone: **+$17.357** improvement, 10 actions, 0 parent winners cut, same-sample robust pass.
- F6.5 +60m upper-wick cut: **+$8.696** improvement, same-sample robust pass.
- Layered same-sample: **+$26.052** improvement; PnL +$64.630 -> +$90.683; PF 1.266 -> 1.419; DD $56.530 -> $39.317.

True-OOS scoreboard after F6.10:
- 3 Friday trades
- parent PnL **-$2.312**
- **0 EARLY10 triggers**
- **0 F6.5 triggers**
- management delta **$0.000**

## What must NOT be done

- Do not retune EMA7, body<50%, +10m, upper-wick>=50%, or +60m from these three OOS observations.
- Do not call F6.9 OOS-confirmed; it has had zero OOS actions.
- Do not call F6.9 OOS-failed; its trigger has also occurred zero times.
- Keep accumulating genuinely unseen Fridays with the exact frozen definitions.

## Execution

- Successful workflow run: **32041704651**
- Artifact: `f610-output`, ID **9292086244**
- Script: `research/f610_friday_early_sink_true_oos.py`
- Workflow commit: `8c042514eb63d8de26d73a5066c3ca4b80fdabdd`
- Live BBC untouched.
