# BNB F85/F15 Transfer — M2 Exact Frozen BTC Signal — B27EE

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Continue only from B27ED M1, which supported all four LONG habitats and SHORT_2000 on BNB. B27EE asks one question only:

> Does the exact frozen BTC causal entry-signal logic itself transfer to BNB without changing clocks, levels, confirmation, next-open entry, or habitat filters?

This is a structural signal-quality milestone, not a TP/SL/PnL optimization.

## Instrument and data
- Target: Binance USD-M BNBUSDT perpetual.
- Control: BTCUSDT using the exact same adapter.
- Raw 5m Binance Vision data.
- Frozen analysis span: 2020-01-01 <= ts < 2026-08-26.
- Frozen partitions: external 2020-01-01..2022-01-01; development 2022-01-01..2025-01-01; reference_validation 2025-01-01..2026-07-30; august diagnostic only.
- Weekday execution starts only.
- Raw coverage for both symbols must be >=99.5%.

## Exact frozen BTC LONG signal
Reuse `bbc_f85_f15_signals.LongF85Session` unchanged.

Habitats:
- ALT_0330 03:30 UTC, including TOUCH_FIRST_HALF: first F85 touch elapsed <=195 minutes.
- RAW_0530 05:30 UTC, including RANGE_COMPLETED_SECOND_HALF: frozen range completion elapsed >=165 minutes.
- LONDON 08:00 UTC, no additional habitat filter.
- RAW_2330 23:30 UTC, including RANGE_COMPLETED_SECOND_HALF.

Common sequence:
completed 5h30 reference -> frozen H/L/R -> first High K1 with Low visits=0 -> completed causal leave -> first pre-H2 F85 touch -> same raw 5m bar closes >F85 -> candidate only at the next raw 5m open when F35 < open < H.

The first F85 touch is decisive. If it does not close >F85, the session ends. No later touch may rescue it.

## Exact frozen BTC SHORT signal
Reuse `bbc_f85_f15_signals.ShortF15Session` unchanged.

SHORT_2000:
completed 20:00 UTC reference -> frozen H/L/R -> first Low K1 with High visits=0 -> completed causal leave -> first pre-H2 F15 touch -> same raw 5m bar closes <F15 -> candidate only at next raw 5m open when L < open < F65.

The first F15 touch is decisive. No later-touch rescue.

## Causality contract
- Adapter sees bar-open and completed bar-close events only.
- Confirmation can only be learned at bar close.
- Candidate can only emit on the following bar open.
- No future H2, exit, later candle, or whole-window outcome may influence candidate generation.
- Exact BTC adapter source code is imported; no BNB-specific strategy branch is allowed.

## Post-entry structural diagnostic
Only after a candidate has emitted, classify the first later event from its entry bar through frozen execution end:
- LONG `H2`: first bar high >= H before completed close < L.
- SHORT `H2`: first bar low <= L before completed close > H.
- if H2 and opposite break occur on the same bar, classify `AMBIGUOUS` and do not count it as H2 success.
- otherwise classify `OPPOSITE_BREAK` or `NO_H2_BY_END`.

This future classification is diagnostic only and cannot alter signal emission.

## Outputs
Persist one row per emitted signal and summary by source × partition plus pooled-major:
- emitted signal count;
- H2 count;
- opposite-break count;
- ambiguous count;
- no-H2 count;
- H2 hit rate among all emitted signals;
- resolved H2 win rate H2/(H2+opposite);
- median minutes entry->H2;
- BTC control values from the same engine.

No PnL, PF, expectancy, leverage, or strategy optimization is allowed.

## Frozen transfer gate
A BNB habitat passes B27EE only if all are true:
1. pooled-major BNB emitted signals >=20;
2. each major partition contains >=5 BNB emitted signals;
3. pooled-major BNB H2 hit rate >=70%;
4. each major partition BNB H2 hit rate >=60%;
5. pooled-major BNB resolved H2 win rate >=75%;
6. pooled-major BNB H2 hit rate is no more than 10 percentage points below exact BTC control for the same habitat.

Overall B27EE is `SUPPORTED` only if at least 3 of 4 LONG habitats pass and SHORT_2000 passes.

These gates are frozen before result-bearing execution and may not be changed after BNB results are observed.

## Mandatory assertions
1. B27ED M1 persisted status is supported before B27EE execution.
2. Exact `bbc_f85_f15_signals` adapters are reused unchanged.
3. Frozen clocks and habitat filters equal BTC B27DW/B27DX lineage.
4. No signal occurs on confirmation close; only next-bar open.
5. First touch remains decisive.
6. Post-entry outcome classification begins only after candidate emission and cannot influence eligibility.
7. No BNB-specific clock, level, filter, TP, SL, PnL or parameter sweep.
8. Raw 5m coverage >=99.5% for BTC and BNB.

**Research only. Stop after B27EE M2 result persistence. Do not run M3 automatically.**
