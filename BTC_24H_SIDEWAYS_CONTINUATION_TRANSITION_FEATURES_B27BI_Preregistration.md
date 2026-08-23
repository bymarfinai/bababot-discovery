# B27BI — BTC 24H SIDEWAYS Continuation-vs-Transition Feature Audit — Preregistration

## Purpose
Determine whether the **first causal 4H bar currently labeled SIDEWAYS after a directional regime** contains enough already-known information to distinguish:

- continuation-like pause: `BULL -> SIDEWAYS -> BULL` or `BEAR -> SIDEWAYS -> BEAR`;
- genuine directional transition: `BULL -> SIDEWAYS -> BEAR` or `BEAR -> SIDEWAYS -> BULL`.

This is a regime-detector anatomy experiment only. It does **not** redesign SIDEWAYS and does not test LONG/SHORT entries, stops, targets, fees, WR, PF, or PnL.

The terms `continuation-like pause` / `transition` describe detector-state paths only. B27BI does not infer participant accumulation, distribution, reaccumulation, or redistribution from price alone.

## Frozen upstream lineage
Reuse unchanged:
- B27AG/B27BG `SwingRegime(slb=5, sa=0.5)` semantics;
- completed 4H UTC bars only;
- EMA7 / EMA20 / ATR14 exact existing implementation;
- causal swing confirmation exactly as existing detector;
- a 4H state becomes available only at `bar_start + 4h`;
- B27BH bracketed SIDEWAYS episode identities and outcome classes.

B27BG and B27BH persisted results must remain present and unchanged. B27BE/B27BF also remain historical and are not modified.

## Data universe
- BTCUSDT 5m repository source.
- Expected identity: exactly **698,112 rows / 100% coverage**.
- All seven calendar days.
- Existing major partitions:
  - external: 2020-01-01 through 2021-12-31;
  - development: 2022-01-01 through 2024-12-31;
  - reference_validation: 2025-01-01 through 2026-07-29.
- August telemetry may be reported separately but does not decide the primary readout.
- Partition boundaries are reporting boundaries only and do not reset detector state.

## Frozen cohort
Only complete SIDEWAYS episodes satisfying all of the following:
1. the immediately preceding effective 4H state is `BULL` or `BEAR`;
2. the SIDEWAYS episode is contiguous in 4H effective time;
3. the first subsequent non-SIDEWAYS state is `BULL` or `BEAR`;
4. no 4H gap occurs across the bracket;
5. the episode belongs to a major partition by its first SIDEWAYS effective timestamp.

Expected B27BH identity to reproduce before any new result is accepted:
- complete directionally bracketed SIDEWAYS episodes = **1,023**;
- same-state resume = **527**;
- opposite-state transition = **496**;
- BULL origin total = **532**;
- BEAR origin total = **491**.

Outcome labels are used only after episode identity is fixed:
- `RESUME` if exit directional state equals origin directional state;
- `TRANSITION` if exit directional state is the opposite directional state.

## Causal observation point
All candidate explanatory features are frozen **at the first SIDEWAYS bar only**, using information available when that 4H bar completes.

No later SIDEWAYS bar, episode duration, eventual exit bar, future return, future High/Low break, or future regime state may enter any explanatory feature.

## Frozen detector-state snapshots
The exact existing `SwingRegime` process is reproduced, but B27BI additionally records the detector's internal counters **after processing each completed 4H bar** and before any future bar exists:
- `hh`, `hl`, `lh`, `ll`;
- EMA7, EMA20, ATR14;
- source 4H OHLC.

Recording counters does not change state semantics.

## Frozen origin-normalized rule clauses
Let `origin_sign = +1` for BULL origin and `-1` for BEAR origin.

For a BULL-origin first SIDEWAYS bar:
- `structure_high_ok = hh >= 2`;
- `structure_low_ok = hl >= 2`;
- `ema_order_ok = EMA7 > EMA20`;
- `close_side_ok = close > EMA20`.

For a BEAR-origin first SIDEWAYS bar:
- `structure_high_ok = lh >= 2`;
- `structure_low_ok = ll >= 2`;
- `ema_order_ok = EMA7 < EMA20`;
- `close_side_ok = close < EMA20`.

Define:
- `directional_evidence_score` = number of the four origin-direction clauses still true, range 0..3 for a bar labeled SIDEWAYS;
- `failed_clause_mask` = exact four-bit failure identity;
- `aligned_structure_strength` = `min(hh,hl)` for BULL origin, `min(lh,ll)` for BEAR origin;
- `opposite_structure_strength` = `min(lh,ll)` for BULL origin, `min(hh,hl)` for BEAR origin.

## Frozen continuous causal features
All are measured at the first SIDEWAYS completed 4H bar and normalized by that bar's ATR14 where applicable:

1. `dir_ema_spread_atr = origin_sign * (EMA7 - EMA20) / ATR14`;
2. `dir_close_ema20_atr = origin_sign * (close - EMA20) / ATR14`;
3. `dir_ema7_slope_atr = origin_sign * (EMA7[t] - EMA7[t-1]) / ATR14[t]`;
4. `dir_ema20_slope_atr = origin_sign * (EMA20[t] - EMA20[t-1]) / ATR14[t]`;
5. `dir_body_atr = origin_sign * (close - open) / ATR14`;
6. `bar_range_atr = (high - low) / ATR14`;
7. `prior_directional_age` = consecutive completed 4H intervals in the immediately preceding BULL/BEAR episode, known before the first SIDEWAYS state becomes effective.

No alternative indicators or thresholds may be added after results are seen in B27BI.

## Required outputs
For pooled-major, every major partition, and separately by BULL-origin / BEAR-origin:

1. RESUME vs TRANSITION N and rate;
2. distribution of `directional_evidence_score` by outcome: mean, median, P25, P75;
3. RESUME rate by evidence score 0/1/2/3;
4. failed-clause-mask counts and RESUME rates;
5. for each individual rule clause, outcome rate when retained vs failed;
6. aligned/opposite swing-strength distributions;
7. each frozen continuous feature: RESUME median, TRANSITION median, median difference, and rank AUC where RESUME is the positive class;
8. feature effect direction consistency across the three major partitions;
9. BULL-origin and BEAR-origin results kept separate before any pooled interpretation.

AUC is descriptive rank separation only; no fitted classifier, no train/test optimization, and no threshold search are allowed.

## Frozen primary readout
Call `B27BI_DIRECTIONAL_EVIDENCE_SUPPORTS_CONTINUATION_PAUSE` only if **both** origin states satisfy all of the following:

1. pooled-major median `directional_evidence_score` is higher for RESUME than TRANSITION;
2. the RESUME-minus-TRANSITION mean evidence-score difference is positive in **each of the three major partitions**;
3. at least one of the four origin-direction clauses has the same qualitative relationship to RESUME in all three major partitions;
4. no result requires looking beyond the first SIDEWAYS completed 4H bar.

Otherwise call `B27BI_FIRST_SIDEWAYS_FEATURES_INSUFFICIENT_OR_UNSTABLE`.

This readout does **not** promote a new SIDEWAYS rule. Any hysteresis, inherited-state, confirmation, or pause-vs-transition classifier requires a separate preregistered redesign experiment.

## Mandatory assertions
1. exactly 698,112 5m rows and 100% source coverage;
2. every complete 4H bar has exactly 48 5m constituents;
3. exact B27BH bracketed episode identity reproduces 1,023 / 527 / 496 / 532 / 491;
4. every feature timestamp equals the first SIDEWAYS state's causal availability timestamp;
5. no future state or future price is used in explanatory features;
6. BULL/BEAR/SIDEWAYS labels reproduce the existing detector exactly;
7. recording swing counters does not alter regime labels;
8. no live BBC file or live trade rule is modified.

## Next step — explicitly out of scope
If causal separation is found, the next experiment may preregister a **new detector-state redesign** that distinguishes directional pause from genuine transition. B27BI itself does not change the detector.

Research only. Live BBC unchanged.
