# BTC MTF Bull Cascade B21 — Preregistration

**Status:** PREREGISTERED — no result-bearing B21 analysis may change the definitions below.

## Question

Does a BTC bullish regime propagate in a repeatable bottom-up sequence from **5m → 15m → 1h → 4h → 1d**, and do cascades that reach the larger timeframes have materially stronger forward outcomes than cascades that die at lower stages?

This is **not** B20. B20 tested whether an already-aligned MTF strong-trend snapshot was directly tradable. B21 tests the **transition path and propagation timing** between timeframes.

## Data

- Instrument: Binance USD-M `BTCUSDT` perpetual.
- Source: public Binance Vision futures klines.
- Base resolution: 5 minutes.
- Warm-up acquisition begins 2019-09-01 UTC when available.
- Result-bearing period begins 2020-01-01 UTC.
- End: last complete day available to the runner, hard capped at 2026-08-21 00:00 UTC for B21 V1.
- No L2, tick replay, news, OI, funding, or external labels are required in B21 V1.

## Frozen partitions

- `external`: 2020-01-01 <= t < 2022-01-01
- `development`: 2022-01-01 <= t < 2025-01-01
- `reference_validation`: 2025-01-01 <= t < 2026-07-30
- `august`: 2026-08-01 <= t < 2026-08-21

No partition may be moved after results are seen.

## Causal timeframe construction

The 5m source is resampled into 15m, 1h, 4h, and 1d bars. A timeframe state becomes observable only **after that timeframe bar has closed**. Its completed state is then forward-filled to the 5m research clock. No partial higher-timeframe candle is used.

## Frozen bullish-state definition

One primary state definition is used on every timeframe:

`BULL = SMA7 > SMA25 > SMA99 AND close > SMA25`

All inputs refer to the just-completed candle of that timeframe. This deliberately reuses the transparent B20 `S1_STACK` core rather than inventing a new state definition after observing B21 outcomes.

B21 does **not** optimize MA lengths, add slope thresholds, or retune state definitions on OOS partitions.

## Seed and propagation definitions

A `5m_seed` occurs when the causal 5m BULL state changes from OFF to ON.

For every seed, search the next **7 calendar days** for the first OFF→ON transition of:

1. 15m
2. 1h
3. 4h
4. 1d

A transition may occur at the same research timestamp as a lower-timeframe transition because multiple completed candles can become observable simultaneously.

### Ordered cascade

An `ORDERED_D1_CASCADE` requires all four higher-timeframe transitions to exist within 7 days and:

`seed_5m <= on_15m <= on_1h <= on_4h <= on_1d`

No maximum per-leg lag is optimized in V1. The actual lag distributions are measured instead.

### Stage reached

Each seed is assigned the deepest **ordered** stage reached within 7 days:

- `S0_5M`
- `S1_15M`
- `S2_1H`
- `S3_4H`
- `S4_1D`

If a higher timeframe flips out of order, deeper stages are not credited until the required lower ordered transitions have occurred.

### Fresh cascade diagnostic

A seed is `FRESH` when 15m, 1h, 4h, and 1d are all OFF immediately before the seed. This is descriptive only; B21 V1 does not select a trading rule from FRESH vs non-FRESH.

## Frozen forward diagnostics

From the seed open, compute forward results over 24h, 72h, and 168h:

- close-to-close return;
- maximum favorable excursion (MFE);
- maximum adverse excursion (MAE).

Predeclared descriptive pump flags:

- `MFE3_72H`: 72h high reaches +3% before the horizon ends;
- `MFE5_72H`: 72h high reaches +5%;
- `MFE8_168H`: 7d high reaches +8%.

These flags are **diagnostics**, not trade targets and not promotion gates.

## Primary analyses

For each partition independently:

1. Count 5m seeds and stage-reach frequencies.
2. Measure ordered-cascade completion rate to 15m, 1h, 4h, and 1d.
3. Measure median and quartile propagation lags for each leg.
4. Compare 24h/72h/168h forward return, MFE, MAE, and pump-flag rates by deepest ordered stage.
5. Repeat the same summary for FRESH seeds.
6. Measure whether stage depth is monotonically associated with stronger forward MFE / positive 72h outcomes.

## Near-invariant diagnostic

B21 may describe a propagation characteristic as a **near-invariant candidate** only if the same directional property is present in all three major partitions (`external`, `development`, `reference_validation`) and each relevant cohort has N >= 30.

Examples of allowable conclusions:

- deeper ordered stage consistently has higher MFE5_72H rate;
- successful D1 cascades consistently pass 15m before 1h before 4h before 1d;
- propagation lag is consistently concentrated in a similar range.

B21 must **not** call anything "certain", "100%", or "invariant" merely because of a small August sample.

## B21 interpretation gates

`B21_PROPAGATION_SUPPORTED` requires, in each major partition:

- at least 30 `S4_1D` ordered cascades OR, if S4 is naturally rarer, at least 30 `S3_4H` cascades and the S4 count is reported without extrapolation;
- deeper stages show non-decreasing `MFE5_72H` rate from S1 through the deepest sufficiently sampled stage, allowing at most one <= 5 percentage-point local violation due sampling noise;
- deepest sufficiently sampled stage has higher `MFE5_72H` rate and higher median 72h MFE than `S0_5M` in every major partition.

`B21_EARLY_ENTRY_CLUE` is descriptive only and requires the same early stage (S1 or S2) to already outperform S0 on `MFE5_72H` by >= 10 percentage points in all three major partitions with N >= 50 each.

Failure of these gates rejects the **frozen B21 propagation hypothesis**, not every possible MTF regime model.

## Anti-overfit rules

- No outcome-based tuning of MA lengths.
- No post-result change to 7-day propagation horizon.
- No OOS retuning.
- No threshold sweep on lags.
- No new indicators after seeing validation.
- August is diagnostic only.
- Historical B20 results remain unchanged.
- Live BBC remains untouched.
