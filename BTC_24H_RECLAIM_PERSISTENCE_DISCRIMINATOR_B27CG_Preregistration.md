# B27CG — BTC 24H Reclaim Persistence Discriminator + No-Boundary Anatomy — Preregistration

## Purpose
1. Find causal observable signs that a first-retest reclaim after direct Low breakdown is less likely to rebreak the Low within the same 4H block.
2. Determine whether B27CE `NO_BOUNDARY_BY_BLOCK_END` cases are mainly flat/chop-like or directional movement that simply remains inside the previous 4H H-L range.

This is anatomy/discriminator research only. It does not prove economic causation and does not define a trade, stop, TP, fee, PF, PnL, expectancy, or live rule.

## Frozen source cohort
Source: `BTC_24H_DIRECT_BREAK_RETEST_SHORT_B27BZ_Events.csv`.

Include exact major-partition rows with `retest_class == RETEST_RECLAIMED`. Must reproduce 734 total = external 202 + development 336 + reference_validation 196.

The reclaim is confirmed at `retest_complete_ts`. Rows with no raw 5m bar after reclaim confirmation before block end are `NO_FOLLOWTHROUGH_WINDOW` and excluded from directional denominators. Eligible identity must reproduce B27CE: external 202 / development 333 / validation 194 / pooled OOS 396 / pooled major 729.

## Frozen outcome
From the first raw 5m bar after reclaim confirmation through the same 4H block end:
- `REBREAK_LOW`: first strict completed `close < L` before any `close > H`;
- `HIGH_BREAK`: first strict completed `close > H` before any `close < L`;
- `NO_BOUNDARY`: neither strict boundary close before block end.

`PERSISTENT_LIKE = HIGH_BREAK or NO_BOUNDARY`.
This label means only no Low rebreak within the remaining same 4H block.

## Frozen causal candidate signs
No threshold may be added after results are observed.

### Available at reclaim confirmation
- `RECLAIM_C05`: reclaim candle close >= L + 0.05*R4.
- `RECLAIM_C10`: reclaim candle close >= L + 0.10*R4.
- `RECLAIM_STRONG_BODY`: reclaim candle is bullish, body/range >= 0.50, and close position in candle range >= 0.75.
- `QUICK_RECLAIM`: B27BZ break-completion -> reclaim-start delay <= 10 minutes.
- `SLOW_RECLAIM`: same delay >= 30 minutes.
- `TIME_LEFT_120`: at least 120 minutes remain in the 4H block after reclaim confirmation.

### Causal confirmation signs after reclaim
These signals become available only when their stated bars have completed; any case rebreaking before the signal completes is signal-false.
- `HOLD_5M_ABOVE_L`: first post-reclaim 5m close > L.
- `HOLD_10M_ABOVE_L`: first two post-reclaim 5m closes > L.
- `HIGHER_CLOSE_5M`: first post-reclaim close > reclaim candle close.
- `EXT10_CLOSE_BEFORE_REBREAK`: before any Low rebreak, a completed close reaches >= L + 0.10*R4.
- `EXT25_CLOSE_BEFORE_REBREAK`: before any Low rebreak, a completed close reaches >= L + 0.25*R4.

## Discriminator metrics
For every signal report external, development, validation, pooled OOS, pooled major:
- eligible cohort N;
- signal N / prevalence;
- persistent-like N/rate among signal;
- baseline persistent-like rate;
- lift vs baseline;
- rebreak rate among signal.

Also report signal readout by 4H clock for the development-selected signal only.

## Frozen development selection
A signal is development-eligible if:
- development signal N >= 30;
- development persistent-like rate >= 45%;
- development lift vs baseline >= +15 percentage points.

Among eligible signals select the highest development lift. Tie-breaker: earlier observability in this order: reclaim-confirmation signals, 5m signals, 10m signals, extension signals.

Untouched OOS support for the selected signal requires:
- external signal N >=20 and lift >= +5pp;
- validation signal N >=20 and lift >= +5pp;
- pooled OOS signal N >=50, persistent-like rate >=40%, and lift >= +10pp.

If none development-eligible: `B27CG_PERSISTENCE_SIGN_NONE`.
If selected but OOS fails: `B27CG_PERSISTENCE_SIGN_NOT_SUPPORTED`.
If passes: `B27CG_PERSISTENCE_SIGN_SUPPORTED`.

## Frozen NO_BOUNDARY anatomy
For exact eligible `NO_BOUNDARY` rows, calculate from reclaim confirmation through block end:
- final close location `(final_close-L)/R4`;
- final net displacement from reclaim candle close, in R4;
- realized close span `(max_close-min_close)/R4`;
- directionality efficiency = `abs(final_close-reclaim_close)/(max_close-min_close)`, clipped to [0,1], undefined if span=0;
- fraction ending >= +10% R4 above reclaim close (`INTERNAL_UP`);
- fraction ending <= -10% R4 below reclaim close (`INTERNAL_DOWN`);
- fraction with absolute final displacement <10% R4;
- `FLAT_CHOP_LIKE`: abs(final displacement)<10% R4 AND directionality efficiency<0.35;
- `MIXED_INTERNAL`: remaining rows not classified as INTERNAL_UP/INTERNAL_DOWN/FLAT_CHOP_LIKE.

`NO_BOUNDARY` must never automatically be called sideways. It means only no strict close outside [L,H] before block end.

Report NO_BOUNDARY anatomy for major partitions, pooled OOS, pooled major, and each 4H clock.

Research only; live BBC unchanged.