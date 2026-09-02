# ETH London -> New York M10 Pre-Breakout Failure Anatomy — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Diagnose why some M5-supported **F90 EARLY_RECLAIM** entries fail before a strict breakout of the frozen London High, with special attention to the Development partition.

M10 is structural diagnostics only. It does **not** change entry, stop, target, fee, slippage, runner, or portfolio rules.

## Frozen cohort
- ETHUSDT perpetual, raw 5m.
- London reference 08:00–13:30 UTC.
- New York active session 13:30–20:00 UTC.
- LONG K1 OPP0 only.
- Exact persisted M5 `EARLY_RECLAIM` rows with `executed=True`.
- Entry timestamp and actual next-bar-open entry price are reused unchanged from M5.
- Historical partitions remain: external, development, reference_validation, August telemetry.

## Frozen outcome
- `BREAKOUT_WINNER`: first completed post-entry 5m close `> H` occurs before any completed close `< L` and before 20:00 UTC.
- `NON_BREAKOUT_OPPOSITE`: first completed post-entry 5m close `< L` occurs before any strict breakout.
- `NON_BREAKOUT_TIME`: no strict breakout and no opposite break by 20:00 UTC.

H2 is telemetry only and does not define success.

## Frozen pre-breakout observation window
For each trade, analyze raw 5m bars from the actual M5 entry bar through the earlier of:
1. strict-breakout bar,
2. opposite-break bar,
3. final bar before 20:00 UTC.

No bar after strict breakout may contribute to M10 failure signatures.

## Family A — reclaim-hold failure
Frozen boundary ladder:

`F90, F85, F80, F75`

For each boundary, report whether a completed post-entry 5m close falls below the boundary **before strict breakout**.

Also report:
- first breach timestamp;
- minutes entry -> first breach;
- whether price subsequently reclaims F90 with a completed close before terminal;
- whether H2 had already occurred before the breach.

Primary diagnostic is completed-close breach; wick-only movement is not a failure signature.

### Frozen structural screen for Family A
A boundary is tagged `PRE_BO_FAILURE_CANDIDATE` only if:
1. each major partition has at least 10 BREAKOUT_WINNER trades;
2. winner breach rate <=20% in **each** major partition;
3. pooled-major non-winner breach rate >=50%;
4. pooled-major non-winner minus winner breach separation >=30 percentage points.

No intermediate F-levels may be added after seeing the result.

## Family B — progress stall
Frozen checkpoints from actual entry:

`15m, 30m, 45m, 60m`

At each checkpoint, classify only trades still alive and not yet strict-breakout:
- `H2_DONE_NO_BO`: H2 has occurred but strict breakout has not;
- `NO_H2_NO_BO`: neither H2 nor strict breakout has occurred.

For each checkpoint report:
- eligible alive N;
- eventual strict-breakout rate for `H2_DONE_NO_BO`;
- eventual strict-breakout rate for `NO_H2_NO_BO`;
- winner/non-winner counts;
- partition stability.

### Frozen stall screen
A `NO_H2_NO_BO` checkpoint is tagged `STALL_CANDIDATE` only if:
1. at least 10 eligible `NO_H2_NO_BO` cases pooled-major;
2. eventual strict-breakout rate <=50% pooled-major;
3. eventual strict-breakout rate <=60% in every major partition with at least 5 eligible cases.

This is a diagnostic candidate only, not an exit rule.

## Required Development decomposition
For Development specifically report:
- total executed M5 EARLY_RECLAIM N;
- breakout winners vs non-breakout failures;
- Family A breach counts/rates by class;
- Family B checkpoint outcomes;
- median entry -> H2 and entry -> strict-breakout time for winners;
- median entry -> terminal time for non-winners.

## Guardrails
- Do not use PnL to choose a structural signature.
- Do not inspect E15/F50 outcomes when labeling M10 winner/non-winner.
- Do not add EMA, ATR, volume, candle-body, session-clock, or regime filters.
- Do not fine-tune thresholds after seeing results.
- M10 may identify multiple candidates or none.

## Mandatory assertions
1. M5 EARLY_RECLAIM executed cohort reproduces exactly (95 rows expected from M5).
2. Strict-breakout winner terminal requires completed `close > H`.
3. Opposite terminal requires completed `close < L`.
4. No post-breakout bar contributes to Family A or B.
5. F-boundaries equal exact frozen London-range fractions.
6. Checkpoint state is computed causally using only bars completed by that checkpoint.
7. Raw ETH 5m coverage >=99.5%.

Research only. Live BBC unchanged.
