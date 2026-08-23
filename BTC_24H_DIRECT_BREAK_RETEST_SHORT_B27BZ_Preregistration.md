# B27BZ — BTC 24H Direct-Break Retest SHORT Anatomy — Preregistration

## Purpose

B27BE showed that after a 4H-block K1 Low visit with OPP0, the frozen previous-4H Low eventually breaks roughly 70% of the time across regimes. B27BY showed that forcing a pre-second-Low F15 retrace is not a robust full-24H transfer. B27BZ therefore isolates the alternative path that B27BE suggested directly:

**K1 Low pressure -> direct Low close-break before any distinct Low #2 -> retest of the broken Low from below -> bearish extension.**

This experiment is structural anatomy only. No stop, TP economics, fee, PF, PnL, leverage, session filter, regime filter, or live BBC change is allowed.

## Frozen source cohort

Reuse exactly the persisted B27BE detail cohort:
- BTCUSDT raw 5m archive used by B27BE/B27BY;
- all seven calendar days;
- six sequential 4H blocks per day;
- previous completed 4H High/Low frozen as `H`/`L`;
- exact B27BE `K1 + OPP0` identities;
- major partitions external / development / reference_validation;
- exact major K1 OPP0 identity must reproduce: external 862, development 1264, reference_validation 641, pooled major 2767.

No Asia/London/New-York label may be used for selection.

## Direct-break definition

`DIRECT_LOW_BREAK` requires all of the following:
1. B27BE K1 Low visit exists and OPP0 is true;
2. the first strict boundary close after K1 is a completed raw 5m `close < L`;
3. at that moment there has been exactly one distinct Low visit episode in the block: K1 itself;
4. therefore no distinct Low #2 occurred before the break.

A Low break that occurs only after Low #2 is NOT part of B27BZ.

The breakdown signal becomes known only after the 5m break candle completes. Any retest search starts from the NEXT raw 5m candle.

## Broken-L retest

After a causal direct Low break, scan forward within the same 4H observation block.

The first later raw 5m bar with `high >= L` is the broken-L retest arrival.

Classify it causally at completion:
- `RETEST_ACCEPTED_BELOW`: retest bar `close <= L`;
- `RETEST_RECLAIMED`: retest bar `close > L`.

Only `RETEST_ACCEPTED_BELOW` creates a continuation-confirmation candidate. The confirmation is known at that retest bar close; post-confirmation evaluation starts from the NEXT 5m bar.

No ATR buffer, percentage buffer, EMA, candle-body rule, or alternate retest price is allowed.

## Frozen bearish-extension milestone

Let previous-4H range `R4 = H - L`.

Freeze one structural extension milestone only:

`EXT15 = L - 0.15 * R4`.

Starting strictly after an accepted retest completes, scan until the end of the same 4H observation block:
- bearish extension success: first later bar with `low <= EXT15`;
- reclaim invalidation: first later completed 5m `close > L`;
- if both occur on the same 5m bar, classify `AMBIGUOUS_EXTENSION_RECLAIM` and do NOT count it as success;
- if neither occurs by block end, classify `UNRESOLVED_BLOCK_END`.

EXT15 is a structural milestone, not a trading TP.

## Required outputs

For external, development, reference_validation, pooled OOS, pooled major, and pooled-major regime/clock diagnostics report:
- K1 OPP0 N;
- direct Low-break N and rate;
- broken-L retest arrivals and retest/direct-break rate;
- accepted-below retests and acceptance rate;
- EXT15 successes after accepted retest;
- reclaim / ambiguous / unresolved counts;
- EXT15 success rate among accepted retests;
- median minutes direct-break -> retest;
- median minutes accepted-retest confirmation -> EXT15.

Persist one row per B27BE K1 OPP0 block with full causal timestamps and classifications.

## Frozen support gate

`B27BZ_DIRECT_BREAK_RETEST_SUPPORTED` only if ALL hold:
1. exact B27BE major K1 OPP0 identity reproduces: 862 / 1264 / 641;
2. every direct-break classification occurs before any distinct Low #2;
3. each major partition has at least 100 direct-break signals;
4. each major partition has at least 30 accepted-below retests;
5. EXT15 success rate among accepted retests is >=65% in external, development, and reference_validation separately;
6. pooled OOS EXT15 success rate is >=65%;
7. no future regime state, session label, stop, target economics, or post-hoc parameter selection is used.

`B27BZ_HIGH_QUALITY_70` additionally requires EXT15 success >=70% in all three major partitions for this exact frozen geometry.

If the support gate fails, verdict is `B27BZ_DIRECT_BREAK_RETEST_NOT_SUPPORTED` and no geometry may be rescued inside B27BZ.

Research only. Live BBC unchanged.
