# B27BP — BTC 24H BULL→SIDEWAYS 5m Pre-Second-Retest Anatomy — Preregistration

## Purpose

Test the exact causal microstructure the user described inside a BULL→SIDEWAYS transition: freeze the latest causally confirmed 4H BULL swing low, then observe 5m price action for `Retest #1 -> causal leave -> inter-retest window -> Retest #2` before classifying the eventual detector outcome as RESUME or TRANSITION.

This is regime-structure anatomy only. It does not authorize LONG/SHORT mapping, entry execution, stop, target, fee, WR, PF, PnL, or live changes. The inter-retest window is studied as a structural event window only; no F15/F85 price fraction is optimized or traded in B27BP.

## Frozen lineage

Reuse unchanged:
- BTCUSDT 5m repository source identity: 698,112 rows / 100% coverage;
- exact completed 4H `SwingRegime(5,0.5)` detector;
- B27BH directionally bracketed SIDEWAYS episodes;
- B27BN BULL frozen boundary = latest confirmed swing low (`lsl`) from the immediately preceding completed BULL state;
- B27BO BULL parent identity.

Mandatory identity before results are accepted:
- BULL-origin bracketed SIDEWAYS episodes = 532;
- RESUME = 281;
- TRANSITION = 251;
- pooled OOS BULL-origin = 313.

## Causal monitoring interval

For a BULL-origin SIDEWAYS episode whose first SIDEWAYS state becomes effective at `T1`:
- the prior completed BULL state is already known at `T0 = T1 - 4h`;
- the frozen swing-low boundary is therefore known at `T0`;
- 5m monitoring begins at `T0`, not at `T1`;
- monitoring ends at the completion of the last 4H source bar labeled SIDEWAYS, i.e. at `last_sideways_effective_ts` exclusive on 5m bar starts.

Thus no future SIDEWAYS label is needed to start monitoring. The eventual RESUME/TRANSITION class is used only as retrospective outcome attribution.

## Frozen 5m event semantics

Let `L` be the frozen BULL swing-low boundary.

A 5m bar is a **defended touch** when:
- `low <= L`, and
- `close >= L`.

A **close break** occurs when `close < L`.

### Retest #1

Retest #1 starts at the first defended-touch 5m bar after `T0`.

Consecutive defended-touch bars are one contiguous Retest #1 episode and are not counted as separate visits.

If the first arrival to `L` closes below `L`, classify `BREAK_ON_FIRST_ARRIVAL`; there is no Retest #1 / inter-retest window.

If a close break occurs while the contiguous Retest #1 episode is still active and before a causal leave, classify `BREAK_DURING_R1`; there is no clean inter-retest window.

### Causal leave

After Retest #1, a causal leave exists only after the first completed 5m bar whose `low > L`.

The inter-retest window becomes eligible only at that leave bar's close, i.e. from the next 5m bar start. This mirrors the chronology used in the historical pre-second-touch work: a completed non-touch bar is required before a pre-Retest-#2 window exists.

If no causal leave occurs before the monitoring interval ends, classify `R1_NO_CAUSAL_LEAVE`.

### Retest #2

After the causal leave, Retest #2 is the first later 5m arrival with `low <= L`.

- if that bar closes `>= L`, classify `R2_DEFENDED`;
- if that bar closes `< L`, classify `R2_BREAK`;
- if no later arrival occurs before the monitoring interval ends, classify `CLEAN_WINDOW_NO_R2`.

No ATR tolerance, percentage buffer, EMA threshold, minimum leave distance, minimum time gap, or post-result alternative touch definition is allowed.

## Required outputs

Report for external, development, reference_validation, POOLED_OOS, and POOLED_MAJOR:

1. total BULL-origin episodes and RESUME/TRANSITION split;
2. counts/rates for `NO_R1`, `BREAK_ON_FIRST_ARRIVAL`, `BREAK_DURING_R1`, `R1_NO_CAUSAL_LEAVE`, `CLEAN_WINDOW_NO_R2`, `R2_DEFENDED`, `R2_BREAK`;
3. clean inter-retest-window rate;
4. Retest #2 arrival rate conditional on a clean inter-retest window;
5. RESUME and TRANSITION rates separately for `R2_DEFENDED` and `R2_BREAK`;
6. baseline BULL-origin RESUME rate for comparison;
7. median/P25/P75 minutes from Retest #1 episode end to causal leave completion and from eligible-window start to Retest #2 arrival;
8. median number of 5m bars in the clean inter-retest window before Retest #2;
9. external and reference_validation signs reported separately before pooled interpretation.

## Frozen structural-support gate

Call `B27BP_BULL_5M_TWO_RETEST_GEOMETRY_SUPPORTED` only if all hold:

1. source/detector/parent identity reproduces exactly;
2. frozen swing-low boundary is available for >=95% of pooled-OOS BULL-origin episodes;
3. pooled-OOS clean inter-retest-window N >=40;
4. pooled-OOS `R2_DEFENDED` N >=20 and `R2_BREAK` N >=20;
5. pooled-OOS RESUME rate for `R2_DEFENDED` is greater than for `R2_BREAK`;
6. the same `R2_DEFENDED` minus `R2_BREAK` RESUME-rate sign is positive in external and reference_validation separately, with >=5 observations in each compared cell;
7. all Retest #2 events occur strictly after the completed causal leave;
8. no trading/economic rule or live BBC file is changed.

Otherwise call `B27BP_BULL_5M_TWO_RETEST_GEOMETRY_NOT_SUPPORTED`.

This gate tests only whether the exact two-retest microstructure carries stable continuation-vs-breakdown information. It does not promote an entry.

Research only. Live BBC unchanged.
