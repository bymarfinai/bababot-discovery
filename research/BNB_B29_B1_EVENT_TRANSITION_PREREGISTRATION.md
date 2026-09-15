# BNB B29-B1 — Event-Conditioned Structural Transition — Preregistration

## Objective
Test whether explicit, causally-observable structural event sequences have repeatable directional behaviour across chronological eras. This is a new scientific identity after A2/A3/A4 rejected nearest-analogue directional prediction.

B1 does **not** test entry price, TP, SL, leverage, fees, PnL, or live execution.

## Frozen parent/data identity
- Symbol: BNBUSDT, Binance Vision USD-M futures 5m.
- Exact accepted A1 raw identity: 687,936 rows, start 2020-02-10 08:00:00 UTC, last bar-open 2026-08-25 23:55:00 UTC.
- Exact A1 fingerprint hash: `2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6`.
- No bar at or after 2026-08-26 00:00:00 UTC may be touched.
- Decision grid: A1 15-minute decision timestamps only; all component bars are already closed.

## Fixed event families and expected direction
No event family may be added, removed, narrowed, or redefined after results are observed.

1. `SWEEP_LOW_RECLAIM` -> LONG
   - current `sweep_low_60 == 1`.
2. `SWEEP_HIGH_REJECT` -> SHORT
   - current `sweep_high_60 == 1`.
3. `BREAK_HIGH_HOLD` -> LONG
   - previous 15m decision `break_high_60 == 1` and current `break_high_60 == 1`.
4. `BREAK_LOW_HOLD` -> SHORT
   - previous 15m decision `break_low_60 == 1` and current `break_low_60 == 1`.
5. `BREAK_HIGH_FAIL` -> SHORT
   - previous 15m decision `break_high_60 == 1`, current `break_high_60 == 0`, current `close_location < 0`.
6. `BREAK_LOW_FAIL` -> LONG
   - previous 15m decision `break_low_60 == 1`, current `break_low_60 == 0`, current `close_location > 0`.
7. `COMPRESSION_EXPAND_UP` -> LONG
   - previous `vol_state == COMPRESS`, current `vol_state == EXPAND`, current `disp_atr_15 >= +0.25`.
8. `COMPRESSION_EXPAND_DOWN` -> SHORT
   - previous `vol_state == COMPRESS`, current `vol_state == EXPAND`, current `disp_atr_15 <= -0.25`.
9. `PULLBACK_UP_RESUME` -> LONG
   - previous `path_state == PULLBACK_FROM_UP`, current `ret_15 > 0`, current `trend_state in {UP, STRONG_UP}`.
10. `PULLBACK_DOWN_RESUME` -> SHORT
    - previous `path_state == PULLBACK_FROM_DOWN`, current `ret_15 < 0`, current `trend_state in {DOWN, STRONG_DOWN}`.

## Event de-duplication
Within each event family, after an accepted event timestamp, suppress subsequent same-family events for 60 minutes. Different families may occur at the same timestamp and are evaluated independently.

## Frozen outcome diagnostics
From the event decision close, compute close-to-close forward return at:
- +15m
- +30m
- **+60m PRIMARY**
- +120m
- +360m

Directional hit:
- LONG family: forward return > 0
- SHORT family: forward return < 0
- zero return is not a hit.

Also report signed return = forward return multiplied by +1 for LONG / -1 for SHORT.

## Chronological folds
Report separately:
- 2022
- 2023
- 2024
- 2025
- 2026 through frozen cutoff

These are historical robustness folds, not untouched final OOS.

## Frozen promotion gate for an event family
A family is `PROMOTE_TO_B2` only if all are true:
1. pooled event N >= 120;
2. evaluable in >=4 folds;
3. each evaluable fold N >= 15;
4. primary +60m pooled directional hit >= 55.0%;
5. primary +60m Wilson 95% lower bound > 50.0%;
6. primary +60m median signed return > 0;
7. at least 4/5 chronological folds have +60m hit > 50%;
8. worst evaluable fold +60m hit >= 47.5%;
9. 2025 +60m hit >= 52.0%;
10. 2026 +60m hit >= 52.0%;
11. at least 3 of 4 auxiliary horizons (15/30/120/360) have pooled hit >= 52.0%;
12. no single fold contributes >45% of pooled events.

If more than three families pass, freeze at max three using this ranking, decided only after applying the fixed pass gates:
1. higher +60m Wilson lower bound;
2. higher +60m pooled hit;
3. larger pooled N;
4. lexical event name tie-break.

## Global B1 verdict
- `BNB_B29_B1_EVENT_TRANSITION_PASS` if at least one family passes.
- `BNB_B29_B1_EVENT_TRANSITION_REJECT` if no family passes with valid integrity.
- `BNB_B29_B1_DATA_TOOLING_FAILURE` if exact data/fingerprint/causality/integrity checks fail.

## Stop rule
After a valid run, do not redefine these event clauses, change cooldown, switch the primary horizon, weaken gates, or select a failed family because one auxiliary horizon looked attractive. Any such change requires a new scientific identity.

If B1 passes, B2 may study execution only for the frozen promoted family/families. If B1 rejects, do not proceed to entry/TP/SL from this identity.
