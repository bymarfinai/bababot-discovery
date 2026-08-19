# BTC Friday SR82 — External Historical Holdout for Prior-Proven SUPPORT

**FROZEN BEFORE RESULT. Research-only; live BBC untouched.**

## Why this study exists
SR81's combined support/resistance rule failed, but its support-side descriptive result was 11/13 HOLD (84.62%) on the already-inspected 2023-12 to 2026-07 research window. Because selecting SUPPORT after seeing SR81 is post-hoc, that 84.62% cannot itself validate an 80% support rule.

SR82 freezes the exact SUPPORT rule now and tests it unchanged on an earlier historical period that was not used to select the support-side hypothesis.

This is an **external historical holdout**, not forward-live evidence.

## Holdout period
- BTCUSDT USD-M perpetual, official Binance Data Vision 5m archives.
- warmup begins 2019-12-01 UTC.
- evaluation Friday-WIB dates: **2020-01-03 through 2023-11-24 inclusive**.
- this ends before the canonical 2023-12-02 start of the recent Friday research universe.

## Frozen SUPPORT definition
Use exactly the SR80/SR81 causal level construction:
- PDH / PDL
- prior-7-WIB-day high / low
- up to 3 most recent confirmed 1H swing highs / lows from prior 7 days
- pivot span 3 completed 1H bars on each side
- cluster within 0.10 x Friday-start Wilder ATR14(1H)
- cluster price = median member price
- all candidate levels frozen at Friday 00:00 WIB

**Only clusters below Friday-open are evaluated in SR82.** This SUPPORT-only restriction is frozen because it is the exact post-SR81 hypothesis being independently tested; no resistance result may be used as a rescue.

## Frozen prior-proof rule
A support cluster is `PRIOR_PROVEN_SUPPORT` iff during the prior 7 days:
- at least 2 resolved same-side support reactions exist;
- every resolved prior reaction was HOLD;
- zero resolved prior BREAKs.

Prior touch eligibility and outcome are exactly SR81:
- prior 5m candle contains level;
- immediately previous 5m close is > level + 0.10 x touch-time ATR;
- touch-time scale uses latest completed 1H Wilder ATR14;
- reaction distance 0.50 ATR;
- 6h horizon;
- same ambiguity/unresolved handling;
- after an eligible proof touch, scanning resumes after its 6h evaluation window.

No change to the 2-touch or zero-break requirement is allowed.

## Friday holdout outcome
For each PRIOR_PROVEN_SUPPORT first touched during Friday:
- reference scale = Friday-start Wilder ATR14(1H)
- HOLD if level +0.50 ATR occurs before level -0.50 ATR
- BREAK if -0.50 ATR occurs first
- 6h horizon
- ambiguous/unresolved excluded from HOLD-rate denominator
- only first Friday touch counts.

Primary metric = HOLD / (HOLD + BREAK).

## Frozen confirmation gate
Verdict `SR82_EXTERNAL_HOLDOUT_SUPPORT_CONFIRMED` only if ALL:
1. resolved N >= 30
2. overall HOLD rate >=80%
3. zero causality/integrity violations
4. at least 3 calendar years with >=5 resolved observations have HOLD rate >50%
5. no calendar year with >=5 resolved observations has HOLD rate <40%

Otherwise `REJECT_SR82_SUPPORT_80_HOLDOUT`.

Report Wilson 95% interval, yearly rates, source-family composition, and ambiguous/unresolved counts.

## Guardrails
- no threshold, lookback, pivot, clustering, reaction-distance, or horizon changes after result
- no resistance-only, source-family-only, confluence-only, year-only, hour-only, or runner-up rescue
- no use of 2020-2023 output to define a new threshold and then re-score the same holdout
- if SR82 confirms, next step is exact-rule transfer to other pairs and/or true-forward BTC observation; it is still not a guarantee
