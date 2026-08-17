# BTC Temporal Friday F6.6 — Immediate Sink Path Forensic

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — DESCRIPTIVE FORENSIC; STRONG IMMEDIATE-SINK COHORT FOUND  
**Research only:** live BBC untouched  

## Question

Are there Friday 15:00 WIB BUY trades that go below entry immediately and never come back?

## Definitions

No threshold fitting was used. Three natural hindsight path labels were inspected:

1. `NEVER_ABOVE_ENTRY`: after the entry open, no 5m high ever exceeds the entry before the parent trade exits.
2. `FIRST5_RED_NEVER_TRADE_RECLAIM`: the first 5m candle closes below entry, and from the second 5m candle onward no high reaches entry.
3. `FIRST5_RED_NEVER_CLOSE_RECLAIM`: the first 5m candle closes below entry, and from the second 5m candle onward no close reaches entry.

These are descriptive future-path labels, not deployable causal rules.

## Main result

### Strict practical definition: first 5m red, then never trades back to entry

`FIRST5_RED_NEVER_TRADE_RECLAIM`:

- Full: **10 trades, 0W / 10L = 0% WR**
- Discovery: **2 trades, 0W / 2L**
- Validation: **8 trades, 0W / 8L**
- Parent exits: **10 SL / 0 TP / 0 timeout**
- Aggregate parent PnL: **-$42.50**
- Median MFE only **+0.016%**
- Median MAE about **-0.805%**

Thus there is a clean historical cohort where Friday BUY is wrong essentially from the start and never even trades back to the entry after the first completed 5m candle.

Only **2/10** overlap the later `FAILURE_60` state and **0/10** overlap the frozen upper-wick true-failure rule. This means the immediate-sink phenomenon is largely a different, earlier failure mechanism than F6.4/F6.5.

### Slightly looser definition: first 5m red, then never closes back at entry

`FIRST5_RED_NEVER_CLOSE_RECLAIM`:

- Full: **14 trades, 0W / 14L = 0% WR**
- Discovery: **4 trades, 0W / 4L**
- Validation: **10 trades, 0W / 10L**
- Parent exits: **14 SL / 0 TP / 0 timeout**
- Aggregate parent PnL: **-$59.50**

### Literal no-uptick cases

`NEVER_ABOVE_ENTRY`:

- **2 trades, 0W / 2L**
- Both occur in Validation
- Both hit SL
- Median MFE = **0.000%**

## Base-rate context

- Total Friday parent trades: **138**
- First 5m candle red: **58 trades**
- Among those 58, **48 eventually traded back to entry** and **44 eventually closed back at/above entry**.

Therefore a red first 5m candle by itself is not enough to cut; many recover. The high-value question is how to identify the 10 true immediate-sink paths causally before the eventual non-reclaim is known.

## Interpretation

This is a strong research lead:

> Friday has an earlier failure mechanism than `FAILURE_60`: some trades enter, immediately lose acceptance, and never reclaim entry.

However, `never reclaim` is hindsight and cannot itself be used live. The correct next milestone is to inspect the first 5/10/15/20/30 minutes for causal state differences between:

- first-5m-red trades that later recover/reclaim entry, versus
- first-5m-red trades that become true immediate sinks.

The objective is to find an early causal **SINK vs RECOVER** state without reducing Friday coverage unnecessarily.

## Execution

- Workflow run: **32039554266** — success
- Artifact: `f66-output`, ID **9291674006**
- Script: `research/f66_friday_immediate_sink_forensic.py`
- Workflow commit: `b515816a2b128550bb88881852cac9821c842a2e`
- Live BBC untouched.
