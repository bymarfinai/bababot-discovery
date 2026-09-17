# BNB B29-B2E — Frozen Character Economic Anatomy — Preregistration

## Scientific identity
`B29-B2E-v1`

B2E is a diagnostic economic-anatomy phase for the frozen B1J LONG character and the frozen B2 event-close entry concept. It does **not** alter, rescue, or re-select the B1J character or B2 entry rule. It asks whether the already-frozen setup has a repeatable post-entry path asymmetry that is potentially monetizable before any TP/SL is selected.

No TP, SL, leverage, fees, position sizing, dollar PnL, or live orders are selected or authorized in B2E.

## Immutable event universe
B2E must consume accepted B29-A1 artifact `10336102957` directly, specifically `BNB_B29_A1_STRUCTURE_FINGERPRINT.csv.gz` with SHA256:

`eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa`

Expected fingerprint rows: 229,267.
First decision: 2020-02-10 14:15 UTC.
Last decision: 2026-08-26 00:00 UTC.

The historical setup universe is frozen to the B1J winning LONG character with the exact B1/B1J same-family base-event cooldown:
1. Start from every causal `sweep_low_60 == 1` decision timestamp.
2. Apply the 60-minute cooldown to those base sweep events before character filtering.
3. Require an exact t-15m predecessor.
4. Require t-15m `path_state == CONT_DOWN`.
5. Require event `close_location >= 0.50`.
6. Require event `body_range < 0.33`.
7. Entry concept remains `E0_EVENT_CLOSE`: completed event-bar close.

The event universe must match the frozen B1J counts exactly:
- 2022: 97
- 2023: 82
- 2024: 114
- 2025: 93
- 2026 through A1 cutoff: 65
- Total: 451

Any mismatch is a tooling/integrity failure. Fresh raw OHLC data may never create, remove, or select setup timestamps.

## Raw path oracle
The immutable A1 fingerprint artifact does not contain raw OHLC highs/lows, so B2E may fetch Binance Vision USD-M Futures `BNBUSDT` 5-minute klines solely as a **post-entry path oracle**.

Fresh raw 5-minute data is permitted only to measure the high/low/close path after already-frozen event timestamps. It may not alter the event universe.

For every event and evaluated horizon:
- exact 5-minute continuity is required;
- event close must map to the raw 5-minute candle closing exactly at decision timestamp t;
- post-entry path excludes the event candle itself;
- if continuity or anchor matching fails, that event-horizon is invalid rather than silently interpolated.

## Exact post-entry path semantics
For an event decision timestamp `t`:
- event raw bar open is `t-5m`;
- entry reference = close of that event bar at `t`;
- for horizon H, post-entry bars have opens `t, t+5m, ..., t+H-5m` and close by `t+H`;
- `terminal_return_H = close(t+H) / entry_close - 1`;
- `MFE_H = max(post-entry high through t+H) / entry_close - 1`;
- `MAE_H = min(post-entry low through t+H) / entry_close - 1`;
- `adverse_magnitude_H = max(0, -MAE_H)`;
- time-to-MFE and time-to-MAE are measured in minutes from entry timestamp t to the close time of the first 5-minute bar reaching the final horizon-specific extreme.

The event bar itself must never contribute to MFE/MAE.

Frozen horizons:
- +15m
- +30m
- +60m (primary)
- +120m
- +360m

## Immutable endpoint cross-check
Because Binance Vision history can be re-published, raw-path terminal returns must be cross-checked against the accepted immutable A1 artifact.

For H = k × 15m, reconstruct the immutable forward return by chaining exact future 15-minute A1 returns:

`immutable_forward_H = product(j=1..k, 1 + ret_15[t + j*15m]) - 1`

Every required 15-minute timestamp must exist exactly; no A1 history gap may be crossed.

For each valid event-horizon, require:
`abs(raw_terminal_return_H - immutable_forward_H) <= 5e-6`

If the aggregate path-oracle integrity gates below fail, B2E status is `BNB_B29_B2E_DATA_TOOLING_FAILURE`, not a scientific rejection.

## Frozen excursion thresholds
B2E evaluates, but does not select, these symmetric excursion thresholds:
- 0.25%
- 0.50%
- 0.75%
- 1.00%

For each event at the primary +60m horizon and each threshold x:
- positive touch: post-entry high >= entry × (1+x)
- adverse touch: post-entry low <= entry × (1-x)
- `POS_FIRST`: first positive-touch 5m bar occurs before first adverse-touch bar
- `NEG_FIRST`: first adverse-touch 5m bar occurs before first positive-touch bar
- `AMBIGUOUS_SAME_BAR`: both sides are first touched in the same 5-minute bar and neither side was touched earlier
- `NEITHER`: neither side is reached in +60m.

No intrabar ordering may be inferred inside an `AMBIGUOUS_SAME_BAR` candle.

For unambiguous first-touch comparisons:
`positive_first_share = POS_FIRST / (POS_FIRST + NEG_FIRST)`

Ambiguous and neither cases remain reported but are excluded from that denominator.

## Frozen metrics
### Per horizon, pooled and by era where applicable
- valid N
- terminal directional hit (`terminal_return > 0`)
- mean terminal return
- median terminal return
- mean MFE
- median MFE
- mean adverse magnitude
- median adverse magnitude
- `P(MFE > adverse_magnitude)`
- median time-to-MFE
- median time-to-MAE

### Primary +60m threshold anatomy
For each frozen threshold:
- total valid N
- positive reach rate
- adverse reach rate
- POS_FIRST count/rate
- NEG_FIRST count/rate
- AMBIGUOUS_SAME_BAR count/rate
- NEITHER count/rate
- unambiguous N
- positive-first share
- Wilson 95% lower confidence bound for positive-first share
- same metrics separately for 2022, 2023, 2024, 2025, 2026.

### +60m endpoint WIN vs LOSS anatomy
Classify endpoint WIN iff +60m terminal return > 0, otherwise LOSS. Report for each group:
- N
- median MFE60
- median adverse magnitude60
- median time-to-MFE60
- median time-to-MAE60.

This is diagnostic only; endpoint WIN/LOSS is not a TP/SL simulation.

## Integrity gates
B2E integrity passes only if all are true:
1. exact immutable A1 CSV SHA256 and expected 229,267 rows;
2. exact frozen B1J event counts by era and total 451;
3. raw-path availability and immutable-anchor-match coverage >=99.5% overall at +60m;
4. +60m coverage >=99.0% separately in each of 2022, 2023, 2024, 2025, 2026;
5. every accepted path has exact 5-minute continuity;
6. every accepted raw endpoint return matches immutable forward return within 5e-6;
7. no duplicate event timestamps.

Failure of any integrity gate => `BNB_B29_B2E_DATA_TOOLING_FAILURE`.

## Frozen economic-geometry gate
If integrity passes, status is `BNB_B29_B2E_ECONOMIC_GEOMETRY_PROMISING` only if all of the following are true:

### A. Primary sample
- valid +60m N >= 400.

### B. Primary excursion asymmetry
- pooled median MFE60 > pooled median adverse magnitude60.

### C. Threshold plateau
At least one adjacent threshold pair among:
- 0.25% and 0.50%
- 0.50% and 0.75%
- 0.75% and 1.00%

must have **both thresholds separately** satisfy all:
- pooled unambiguous first-touch N >= 120;
- pooled positive-first share >= 55.0%;
- Wilson 95% lower bound > 50.0%;
- positive-first share > 50.0% in at least 4 of 5 eras where era unambiguous N >= 15;
- combined 2025+2026 positive-first share >= 52.0%.

### D. Direction sanity
- reconstructed pooled +60m terminal directional hit >= 57.0%.

If integrity passes but any economic-geometry requirement fails, status is:
`BNB_B29_B2E_ECONOMIC_GEOMETRY_WEAK`.

## Interpretation / stop rule
B2E is anatomy, not optimization. After observing B2E-v1:
- do not change excursion thresholds and call it B2E-v1;
- do not choose a single best threshold and call that a TP;
- do not add filters or remove inconvenient B1J events;
- do not alter the B1J character, cooldown, entry, primary horizon, or geometry gates;
- do not infer intrabar order for same-bar touches;
- do not use B2E to bypass the still-running B2S prospective checkpoint.

`ECONOMIC_GEOMETRY_PROMISING` only permits a separately preregistered B3 TP/SL discovery phase. It is not READY TO TRADE and does not authorize live orders.