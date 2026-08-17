# Friday15 F6.1 — Frozen FAILURE_60 Exit Counterfactual

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — FAIL  
**Research only:** live BBC untouched

## Frozen rule
`FAILURE_60 = alive + progress<=0 + taker<0 + close<=EMA20`; exit at actual +60m open.

## Result
- Parent: **66W/72L, WR 47.83%, +$64.630**
- Managed: **59W/79L, WR 42.75%, +$58.258**
- Delta: **-$6.372**
- Actions: **28**; improved 19; damaged 9
- Winner->loss: **7**; loss->win: **0**

## Chronology
- Discovery: **-$15.305** delta on 15 actions
- Validation: **+$8.933** delta on 13 actions

## Verdict
**FAIL.** A blunt +60m exit on the frozen FAILURE state is not robust. It helps validation but damages discovery and converts 7 eventual winners into losses.

The useful inference is that `FAILURE_60` contains at least two sub-states: true failure and recoverable dip. Do not tune this rule post hoc. The next clean research milestone, if continued, is forensic separation of those two paths using information after +60m but before any action is tested.

## Execution
- Workflow run: **32035658449**
- Artifact: `f61-output`, ID **9290583433**
- No live BBC modification.
