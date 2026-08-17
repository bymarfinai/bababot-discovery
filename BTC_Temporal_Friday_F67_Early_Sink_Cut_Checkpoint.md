# BTC Temporal Friday F6.7 — Causal Early-Sink Cut

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — SIMPLE NO-RECLAIM CUT FAILS; EARLY-SINK LEAD REMAINS ACTIVE  
**Research only:** live BBC untouched

## Question

Can the F6.6 immediate-sink losses be cut before the frozen -0.7% SL using a causal path state?

## Causal detector tested

At +5/+10/+15/+20/+30m:

`EARLY_SINK_t = first 5m red + trade still alive + no completed 5m after the first has traded back to entry`

Action: exit at the actual decision-time open.

This state is fully causal. The 10 F6.6 strict sinks are used only as hindsight labels to measure recall.

## Parent

- 138 trades
- 66W / 72L = **47.83% WR**
- PnL **+$64.630**
- PF **1.266**
- max DD **$56.530**

## Results

### +5m
- 57 actions
- captures 9/10 strict sinks
- also cuts 19 eventual winners
- strategy delta **-$45.323**
- Discovery **-$43.286** / Validation **-$2.036**
- FAIL

### +10m — most informative early hinge
- 29 actions
- captures **9/10 strict sinks**; 9/9 sinks still alive are detected
- 20 non-sink actions
- cuts **8 eventual winners**
- action cohort parent WR **27.59%**
- action PnL **-$41.284 -> -$48.600**
- full strategy delta **-$7.316**
- Discovery **-$21.444**
- Validation **+$14.128**
- max DD improves by **$6.993**
- FAIL overall because recoverable/winning trades are still being clipped

### +15m
- 21 actions; 7/10 strict sinks; 8 winners cut
- strategy delta **-$19.044**
- Discovery **-$25.661** / Validation **+$6.617**
- FAIL

### +20m
- 18 actions; 7/10 strict sinks; 6 winners cut
- strategy delta **-$16.305**
- Discovery **-$18.829** / Validation **+$2.523**
- FAIL

### +30m
- 15 actions; 7/10 strict sinks; 4 winners cut
- strategy delta **-$14.435**
- Discovery **-$15.705** / Validation **+$1.270**
- FAIL

## Interpretation

The early-sink phenomenon is real, but **time-under-entry alone is not sufficient** for management.

The most useful next hinge is +10m because it detects 9/10 strict sinks while they are still alive and materially improves Validation and drawdown, but it damages Discovery by cutting seven eventual winners there.

Therefore the next problem is not whether to abandon the early-sink idea. It is to find a **recovery guard** inside the +10m candidate state:

- true continued sink -> CUT;
- still-below-entry but showing recovery/absorption -> HOLD.

The next clean milestone should inspect causal +10m pressure/recovery structure (progress/depth, bounce, taker flow, EMA position, second-candle morphology and lower-high/lower-low structure), then test a small set of natural mechanism rules without threshold tuning.

## Execution

- Workflow run: **32041088756** — success
- Artifact: `f67-output`, ID **9291967094**
- Script: `research/f67_friday_early_sink_cut.py`
- Workflow commit: `ee63876e5d2ee7d52cbe8745278eedd44fe3a715`
- Live BBC untouched.
