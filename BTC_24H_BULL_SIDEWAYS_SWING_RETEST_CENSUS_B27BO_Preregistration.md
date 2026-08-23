# B27BO — BTC 24H BULL→SIDEWAYS Swing-Retest Census — Preregistration

## Purpose

Answer one narrow regime-structure question: after an existing causal 4H `BULL` state first becomes `SIDEWAYS`, how many **distinct defended retests of the same frozen bullish swing-low boundary** occur before that boundary is finally broken on a completed 4H close?

This is a descriptive detector-anatomy census only. It does not define LONG/SHORT direction, entry, stop, target, fee, WR, PF, PnL, or live behavior.

## Frozen lineage

Reuse B27BN/B27BH exactly:
- BTCUSDT 5m source identity: 698,112 rows / 100% coverage;
- completed UTC 4H bars only, 48 constituent 5m bars;
- existing `SwingRegime(5, 0.5)` labels unchanged;
- B27BH complete directionally bracketed SIDEWAYS episodes;
- B27BN frozen BULL boundary = latest causally confirmed swing low (`lsl`) from the immediately preceding completed BULL state;
- boundary is frozen before SIDEWAYS begins and may not move during the episode.

Mandatory parent identity before accepting results:
- 1,023 directionally bracketed SIDEWAYS episodes total;
- BULL-origin = 532;
- BULL-origin RESUME = 281;
- BULL-origin TRANSITION = 251.

## Frozen retest / break semantics

For each BULL-origin SIDEWAYS episode and each completed 4H SIDEWAYS source bar:

- `touch_or_sweep` = bar low `<= frozen_boundary`;
- `close_break` = bar close `< frozen_boundary` (exactly the B27BN close-break direction);
- `defended_retest_bar` = `touch_or_sweep` AND NOT `close_break`.

A **distinct defended retest visit** starts on a defended-retest 4H bar when the immediately preceding completed SIDEWAYS 4H bar was not a defended-retest bar. Consecutive defended-retest bars therefore collapse into one visit and are not double-counted.

The **first break** is the first completed SIDEWAYS 4H bar whose close is below the frozen boundary.

For episodes with a first break:
- count distinct defended retest visits only on completed SIDEWAYS bars strictly before the first close-break bar;
- also count raw defended-retest bars before break;
- record break age in 4H bars / hours.

For episodes without a close break during SIDEWAYS:
- count distinct defended retest visits over the whole SIDEWAYS episode;
- label them `NO_CLOSE_BREAK_DURING_SIDEWAYS`; they do not enter the primary “retests before break” denominator.

No ATR tolerance, percentage buffer, EMA threshold, fitted cutoff, or post-result visit definition is allowed.

## Reporting cohorts

Primary reporting:
- `external`;
- `reference_validation`;
- `POOLED_OOS = external + reference_validation`.

Development is diagnostic only. Pooled-major may be reported descriptively.

## Required outputs

For BULL-origin episodes with a close break during SIDEWAYS, report:
1. N and share of all BULL-origin episodes;
2. distribution of **distinct defended retest visits before first close break**: 0, 1, 2, 3+;
3. median, P75, P90, and maximum distinct retest visits;
4. raw defended-retest-bar count before break: median / P75 / P90 / max;
5. first close-break age: median / P75 / P90 / max in 4H bars and hours;
6. the same retest-count distribution separately for eventual `RESUME` and `TRANSITION` outcomes, descriptive only;
7. external and reference_validation distributions separately.

For episodes with no close break during SIDEWAYS, report:
- N;
- distinct defended retest visit distribution 0 / 1 / 2 / 3+;
- eventual RESUME vs TRANSITION split.

## Frozen audit gate

This experiment is a census, not a promotion test. Tag `B27BO_BULL_SWING_RETEST_CENSUS_COMPLETE` only if:
1. exact source/detector/parent identities reproduce;
2. frozen BULL boundary is available for >=95% of pooled-OOS BULL-origin episodes;
3. every counted retest occurs on a completed SIDEWAYS bar and strictly before the first close-break bar when a break exists;
4. consecutive defended-retest bars are collapsed exactly as preregistered;
5. pooled-OOS contains at least 30 BULL-origin episodes with a close break during SIDEWAYS;
6. no live BBC file or trading rule is modified.

Otherwise tag `B27BO_BULL_SWING_RETEST_CENSUS_INCOMPLETE`.

## Interpretation boundary

B27BO answers only **how many defended tests of the frozen BULL swing low occur before a confirmed 4H close break** under this exact structural definition. It does not prove accumulation/reaccumulation and does not redesign the regime detector.

Research only. Live BBC unchanged.
