# BNB B29 A3 — Regime-Aware Character Memory Preregistration

## Purpose

A3 is a new scientific identity created after the frozen A2-v1 generic character-memory layer was rejected. A3 tests one explicit hypothesis only: **local structural analogs become more behaviourally useful when analog memory is restricted to a causally-known slow market regime**.

A3 does **not** define or test entry, TP, SL, leverage, fees, PnL, or live execution. It is a prerequisite memory layer only.

## Parent identities

- Pair: `BNBUSDT`, Binance Vision USD-M futures 5m.
- Frozen raw A1 identity: exactly **687,936** bars, first bar `2020-02-10 08:00:00+00:00`, last bar `2026-08-25 23:55:00+00:00`.
- Frozen A1 fingerprint hash: `2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6`.
- No bar at or after `2026-08-26 00:00:00+00:00` may be used.
- Parent A2-v1 is frozen `BNB_B29_A2_CHARACTER_MEMORY_REJECT`; its parameters/results may not be tuned or relabelled.

## Causal slow-regime overlay

At each completed 5m decision timestamp, construct slow features using only bars already closed:

1. `macro_trend_z_24h` = 24h log return divided by 24h realized-volatility scale (`rv_24h * sqrt(288)`).
2. `macro_eff_24h` = absolute 24h close displacement divided by the sum of absolute 5m close changes over 24h.
3. `macro_vol_ratio_6h_24h` = 6h realized volatility / 24h realized volatility.

Frozen categorical mapping:

- Macro trend: `STRONG_DOWN < -1.00`; `DOWN < -0.35`; `FLAT <= +0.35`; `UP <= +1.00`; otherwise `STRONG_UP`.
- Macro efficiency: `LOW < 0.20`; `MID < 0.40`; otherwise `HIGH`.
- Macro volatility: `COMPRESS < 0.80`; `NORMAL <= 1.25`; otherwise `EXPAND`.

`primary_regime = macro_trend + macro_volatility` and is a **hard memory gate**. A query may only retrieve analogs with the same primary regime. Macro-efficiency is a secondary regime attribute and receives a fixed mismatch penalty of `0.25`.

## Local structural similarity

After the hard regime gate, A3 reuses the frozen A2-v1 local similarity identity unchanged:

- same A1 numeric similarity features;
- same A1 categorical features;
- robust scaling fitted only on chronologically eligible memory;
- local categorical mismatch penalty `0.35`;
- candidate neighbors `256`;
- selected analogs `K=64`;
- minimum analogs `48`;
- maximum one selected analog per UTC calendar date.

No hour is a primary selector. Clock features remain context features only.

## Walk-forward chronology

Frozen folds: `2022`, `2023`, `2024`, `2025`, `2026-precutoff`.

For fold year Y:

- query rows are inside year Y (2026 ends at frozen cutoff);
- memory rows must be strictly before the start of Y;
- every memory analog's complete `+360m` behaviour must already be known before Y begins;
- slow-regime state at both query and analog timestamp is computed only from already-closed bars.

The query sampling identity is unchanged from A2-v1: UTC minute `00` and WIB hour divisible by four.

Fixed forward behaviour horizons: `+15m`, `+30m`, `+60m`, `+120m`, `+360m`.

## Frozen gates

### Integrity — all mandatory

- exact frozen raw identity recovered;
- exact A1 fingerprint hash match;
- no post-cutoff data touched;
- finite numeric outputs;
- chronology / behaviour-known guard PASS;
- each fold memory N >= 20,000;
- each fold original query N >= 500;
- each fold evaluable query N >= 500;
- each fold evaluable coverage >= 75%;
- each fold median analog N >= 48.

Any integrity failure => `BNB_B29_A3_DATA_TOOLING_FAILURE`.

### Structural / regime coherence

Pooled medians must satisfy:

- same local `structure_state` >= 55%;
- same local `path_state` >= 60%;
- same primary regime = 100% by construction;
- same macro-efficiency state >= 50%.

### Behavioural memory gate

All are required:

- at least 4/5 pooled horizon Spearman rho values > 0;
- median pooled Spearman rho >= `0.0300`;
- mean pooled sign agreement >= `51.00%`;
- at least 4/5 chronological folds have positive median rho;
- 2025 median rho > 0;
- 2026-precutoff median rho > 0;
- no fold median rho < `-0.0200`.

PASS only if integrity + structural/regime coherence + behavioural memory gate all pass.

## Frozen decision labels

- PASS: `BNB_B29_A3_REGIME_MEMORY_PASS`
- REJECT: `BNB_B29_A3_REGIME_MEMORY_REJECT`
- tooling/data failure: `BNB_B29_A3_DATA_TOOLING_FAILURE`

## Stop rule

After the first valid frozen-identity A3 result, do not change regime thresholds, penalties, K, feature set, query schedule, folds, horizons, or gates in response to that result. A rejection requires a separately named new scientific identity with a new causal hypothesis; it cannot be rescued against the same result surface.
