# ETH London -> New York M7 F90 Early-Reclaim Post-Breakout Extension — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Freeze the M5-supported **F90 EARLY_RECLAIM** entry and calibrate the native ETH reward-side continuation **after a confirmed strict breakout**.

M7 does not install a stop and does not optimize PnL. It asks only:

`F90 early reclaim entry -> strict completed 5m close > London H -> how far does the post-breakout move causally extend?`

## Frozen cohort
- ETHUSDT perpetual, raw 5m.
- London reference 08:00-13:30 UTC.
- New York active session 13:30-20:00 UTC.
- LONG K1 OPP0 only.
- Exact persisted M5 `EARLY_RECLAIM` rows with `executed=True` and terminal `STRICT_BREAKOUT`.
- M5 entry timestamp, entry price, frozen London H/L/R, and strict-breakout bar are reused unchanged.
- Historical partitions unchanged: external, development, reference_validation, August telemetry.

## Frozen causal stage order
1. F90 touch occurred pre-H2 under M2 chronology.
2. M5 EARLY_RECLAIM confirmed on a completed raw 5m close > F90.
3. Entry occurred at the next raw 5m bar open.
4. Strict breakout is the first completed post-entry raw 5m candle with `close > H` before any completed close < L.
5. M7 extension scoring begins only from the **next raw 5m bar after the strict-breakout bar completes**.
6. Any extension touched intrabar on the strict-breakout bar itself is telemetry only and cannot count as a causal post-breakout extension.
7. All scoring ends at 20:00 UTC; no later event is used.

## Frozen extension ladder
With `R = H-L`:
- E05 = H + 0.05R
- E10 = H + 0.10R
- E15 = H + 0.15R
- E20 = H + 0.20R
- E25 = H + 0.25R
- E30 = H + 0.30R

No intermediate or farther extension is added after result inspection.

## Required trade-level outputs
For each confirmed-breakout cohort row persist:
- partition/date;
- M5 entry timestamp and actual entry fraction;
- strict-breakout bar timestamp;
- same-breakout-bar overshoot flags for E05..E30;
- first causal post-breakout touch timestamp for E05..E30;
- minutes from breakout-bar completion to each causal extension;
- maximum causal extension fraction reached by 20:00 UTC.

## Required summaries
For each major partition, August telemetry, and POOLED_MAJOR:
- confirmed-breakout denominator N;
- causal hit count/rate for E05..E30;
- same-breakout-bar overshoot rate as telemetry;
- median minutes to each causal extension;
- conditional continuation rates E10|E05, E15|E10, E20|E15, E25|E20, E30|E25;
- distribution of maximum causal extension achieved.

## Frozen structural target screen
An exact extension is tagged `STRUCTURAL_TARGET_CANDIDATE` only if:
1. each major partition has at least 10 confirmed-breakout cohort rows;
2. causal post-breakout hit rate is >=80% in **each** external, development, and reference_validation;
3. pooled-major causal hit rate is >=85%.

If multiple adjacent extensions pass, report the full supported family. Do not select the farthest or highest-rate level as a final TP in M7.

## Interpretation guardrails
- H2 is not a target and is not used for M7 selection.
- Same-breakout-bar overshoot cannot rescue a failed causal extension.
- No stop, PF, PnL, fee, slippage, leverage, runner, portfolio lock, clock filter, ATR/EMA/volume, or candle-shape filter is allowed.
- Do not change F90 EARLY_RECLAIM entry semantics.
- M7 calibrates reward habitat only; any economic TP decision must wait for a later stage that combines the separately calibrated risk side.

## Mandatory assertions
1. M5 EARLY_RECLAIM strict-breakout cohort identities/timestamps reproduce exactly.
2. Every cohort row has a completed strict-breakout bar with `close > H`.
3. Causal extension scoring begins strictly after breakout-bar completion.
4. Extension ladder prices equal exact frozen H + eR geometry.
5. Hit monotonicity holds: E30 hit implies E25/E20/E15/E10/E05 hit, etc.
6. No event at/after 20:00 UTC is scored.
7. Raw ETH 5m coverage >=99.5%.

Research only. Live BBC unchanged.