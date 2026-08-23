# B27CJ — BTC 24H Post-Rebreak T10 Profit-Lock Hybrid — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Mirror the F85/B27AC hybrid exit methodology on the current BTC 24H SHORT reclaim lineage, while preserving the user's requested research order: TP architecture first, SL/economics later.

B27CJ is anatomy only. It does **not** define an entry, SL, fee, WR, PF, PnL, leverage, or live BBC rule.

## Frozen source and milestone
Source: persisted `BTC_24H_POST_REBREAK_TP_FRONTIER_B27CI_Detail.csv`.

Use only major partitions with `followthrough_eligible == True`. Exact B27CI eligible identity must reproduce:
- external 147
- development 233
- reference_validation 133
- pooled OOS 280
- pooled major 513.

The frozen milestone is the B27CI selected and OOS-supported target:
- `T10 = L - 0.10 * R4`, where `R4 = H-L`.

B27CJ does not search T7.5/T12.5/T15 or any alternative milestone.

## Fixed-T10 reference
A path is a fixed-T10 reach if, starting on the next raw 5m bar after confirmed Low rebreak, `low <= T10` before the first completed 5m close `> L` or the same 4H block end. This must reproduce B27CI T10 hit counts/rates.

Fixed T10 is the reference exit geometry: a reached path would capture exactly `10% R4` downside extension from L.

## Hybrid rule — SHORT mirror of F85/B27AC

### Phase 1 — before T10 is reached
No SL or discretionary exit is introduced. B27CJ only observes whether T10 is reached under the exact B27CI continuation window.

If T10 is never reached, classify `NO_T10_REACH`; the hybrid is not activated.

### Phase 2 — T10 profit ceiling activation
T10 is considered reached on the first raw 5m bar with `low <= T10`.

After that completed bar:
- T10 becomes a hard resting **profit ceiling** for the SHORT from the **next** raw 5m bar;
- the T10-touch bar cannot be retroactively stopped at T10 because 5m OHLC does not reveal intrabar order;
- if the next/later bar opens at or above the active ceiling, exit at the actual open;
- otherwise, if a later bar trades `high >= active_ceiling`, exit at the active ceiling;
- there is no fixed lower TP after T10 is reached.

### Phase 3 — structural ratchet below T10
After the T10 ceiling is active:
- a strict 3-bar pivot high centered on bar `i-1` becomes known only when bar `i` completes and requires:
  `high[i-1] > high[i-2] AND high[i-1] > high[i]`;
- only pivots whose three bars are at/after the post-rebreak evaluation start may be used;
- if a newly confirmed pivot high is **below** the current active ceiling, the ceiling ratchets downward to that pivot high;
- the ceiling may never move upward;
- a ratchet confirmed at bar `i` close becomes effective only from bar `i+1` and cannot stop bar `i` retroactively;
- one pivot definition only: no ATR, EMA, body, percentage trail, pivot-width sweep, or alternate target.

### Block end
If still running at the 4H block end, exit at the first raw 5m open at `obs_end`. If that bar is unavailable, classify censored rather than inventing an exit.

## Required diagnostics
For external, development, reference_validation, pooled OOS, pooled major, and each six UTC 4H clocks report:
- eligible rebreak N;
- T10 reach N/rate;
- among T10 reachers: T10-ceiling exits, ratcheted-structural-ceiling exits, open/gap exits, time exits;
- preservation rate: realized hybrid exit extension `>= 10% R4` among T10 reachers;
- peak downside extension after T10 reach;
- realized hybrid exit extension below L;
- fixed reference extension = 10% R4;
- delta realized extension vs fixed T10;
- capture ratio and giveback from peak;
- number of ratchets;
- minutes T10 reach -> hybrid exit.

All extension metrics are structural percentages of R4, not trade returns.

## Frozen interpretation gate
`B27CJ_T10_HYBRID_SUPPORTED` requires all:
1. B27CI eligible identity and T10 reach counts reproduce exactly;
2. at least 80 T10 reachers in development, 60 external, and 60 validation;
3. median realized hybrid exit extension is >=10% R4 in each major partition;
4. mean realized hybrid exit extension is >10% R4 in each major partition;
5. T10 preservation rate is >=80% in each major partition;
6. pooled-major mean realized extension exceeds fixed T10;
7. no clock/regime exclusion.

Otherwise verdict is `B27CJ_T10_HYBRID_NOT_SUPPORTED`.

This gate concerns TP management only. Even a PASS would not establish a profitable trade; SL and economics remain separate future work.

Research only. Live BBC unchanged.

<!-- Execution trigger only; no semantic change to the frozen preregistration. -->
