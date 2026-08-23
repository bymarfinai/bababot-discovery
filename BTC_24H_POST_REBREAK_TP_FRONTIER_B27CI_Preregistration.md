# B27CI — BTC 24H Post-Rebreak TP Frontier — Preregistration

## Purpose
Find the structurally realistic downside extension after a confirmed Low rebreak in the B27CE reclaim lineage, before discussing stop-loss geometry.

This is anatomy only. No SL, fee, PF, PnL, expectancy, leverage, or live BBC change.

## Frozen source cohort
Source: `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`.
Include only major partitions with `eligible == True` and `terminal_type == REBREAK_LOW`.
Expected identities:
- external: 149
- development: 237
- reference_validation: 133
- pooled OOS: 282
- pooled major: 519.

`terminal_ts` from B27CE is the completion time of the 5m candle that confirmed `close < L`. B27CI evaluation begins at that timestamp, i.e. the next raw 5m bar after rebreak confirmation, and ends at the same 4H block end.

If `terminal_ts >= obs_end`, classify `NO_FOLLOWTHROUGH_WINDOW` and exclude from extension-rate denominators rather than treating it as zero extension.

## Frozen continuation terminal
After confirmed rebreak, scan raw 5m bars causally. The continuation window ends on the first completed 5m candle with `close > L` (a fresh reclaim above the broken Low), or at block end if no such reclaim occurs.

The low of the fresh-reclaim candle is still part of the pre-reclaim path because the close is only known at candle completion. Therefore if a downside target is touched intrabar and that same candle later closes above L, the target touch is valid and causal.

## Frozen TP ladder
Let `R4 = H-L`. Test downside targets:
- T02.5 = `L - 0.025*R4`
- T05 = `L - 0.05*R4`
- T07.5 = `L - 0.075*R4`
- T10 = `L - 0.10*R4`
- T15 = `L - 0.15*R4`
- T20 = `L - 0.20*R4`
- T25 = `L - 0.25*R4`
- T35 = `L - 0.35*R4`
- T50 = `L - 0.50*R4`.

For each eligible rebreak episode report whether each target is touched before the continuation window terminates, plus minutes from rebreak confirmation to first touch.

Also report maximum downside extension from L as %R4 (P25/P50/P75/P90).

## Required scopes
Report external, development, reference_validation, pooled OOS, pooled major, and all six UTC 4H clocks.

## Frozen development selection
A structural TP candidate is the deepest ladder target whose development hit rate is >=70% with at least 150 eligible development rebreak episodes.

If multiple qualify, choose the deepest. If none qualify, no TP candidate is selected.

Untouched OOS support for that selected target requires:
- external hit rate >=65%;
- reference_validation hit rate >=65%;
- pooled OOS hit rate >=65%;
- no clock/regime exclusion.

Frozen verdicts:
- `B27CI_TP_FRONTIER_SUPPORTED`
- `B27CI_TP_FRONTIER_NOT_SUPPORTED`
- `B27CI_NO_70PCT_TP_CANDIDATE`.

The selected TP is a structural continuation target only. It is not a trading WR and cannot be called profit-optimal until a separately preregistered SL/economic test is run.