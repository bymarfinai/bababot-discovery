# B27DW — Frozen F85 LONG + F15 SHORT20 Raw Closed-5m Signal-Adapter Parity — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Replace canonical-candidate injection with independent causal signal generation from raw BTCUSDT 5m OHLC bars for the already-frozen B27DQ LONG and SHORT20 strategies. B27DW is shadow engineering only: no exchange entry writes and no strategy tuning.

## Frozen LONG signal universe
Recreate exactly the B27DQ/B27DK four operating zones from raw 5m bars:
- `ALT_0330`: 03:30 UTC reference start, 5h30 reference, 09:00-15:30 execution, F85 same-bar reclaim, next-5m-open entry, and frozen TOUCH_FIRST_HALF (`touch_elapsed_min <= 195`).
- `RAW_0530`: 05:30 UTC reference start, same duration/execution geometry, with frozen B27DJ `RANGE_COMPLETED_SECOND_HALF` (final H/L range completion elapsed >=165 min).
- `LONDON`: 08:00 UTC reference start, same F85 same-bar rule, no additional filter.
- `RAW_2330`: 23:30 UTC reference start, same geometry, with `RANGE_COMPLETED_SECOND_HALF`.

Common causal sequence is frozen: completed reference -> H/L/R frozen -> first High K1 with Low visits=0 -> causal leave -> first pre-H2 F85 touch -> that same 5m bar closes >F85 -> candidate appears only at next 5m open if `F35 < open < H`.

## Frozen SHORT20 signal
Reference start 20:00 UTC, 5h30 reference, execution 01:30-08:00 UTC next day. Freeze exact B27DR/B27DS logic: first Low K1 with High visits=0 -> causal leave -> first pre-H2 F15 touch -> same 5m bar closes <F15 -> candidate at next 5m open if `L < open < F65`.

## Causality contract
Signal adapters operate as session state machines with two event types only:
1. completed 5m bar (`on_bar_close`), which may update K1/leave/touch/confirmation state;
2. next 5m bar open (`on_bar_open`), which alone may emit an entry candidate after a prior completed-bar confirmation.

No future H2, exit, later candle, or whole-window outcome may be consulted to emit an entry.
The first F85/F15 touch is decisive: if that first touch fails same-bar confirmation, the session is done, matching frozen research semantics.

## Historical parity controls
Using the same raw 698,112-row BTCUSDT 5m dataset:
- rebuild B27DQ raw four-zone LONG candidate stream and its exact filtered candidate identities;
- rebuild frozen SHORT20 candidate stream;
- compare raw-adapter output against canonical research output using side/source/entry timestamp, entry price, H/L and F-level geometry;
- require 100% candidate identity/order parity and numerical geometry parity within floating tolerance.

Expected control counts before global lock are approximately:
- B27DQ four-zone LONG: 244 all-partition candidates / 242 pooled-major candidates;
- SHORT20: 57 all-partition candidates / 56 pooled-major candidates.
Exact counts are gate values derived from the frozen controls during the run; any mismatch fails.

## End-to-end shadow arbitration
After raw signal parity passes, enrich generated historical entry signals with their already-frozen canonical exit timestamps only for the purpose of replaying the previously-audited one-position arbitration layer. Feed those generated entries into the B27DV shadow control plane and require the pooled-major accepted order to remain exactly 283 = 227 LONG + 56 SHORT20.

This enrichment is not signal generation and cannot influence entry eligibility.

## Failure/phantom tests
- no entry may emit on the F85/F15 confirmation close before the next-bar-open event;
- duplicate bar-open or bar-close delivery must not emit a duplicate signal;
- an H2/opposite-break bar before the first F-touch terminates eligibility;
- first F-touch without same-bar confirmation terminates eligibility;
- reference H/L remain immutable throughout execution.

## Frozen gate
`B27DW_RAW_5M_SIGNAL_PARITY_SUPPORTED` only if:
- LONG raw candidate count/identity/order = 100% canonical parity;
- SHORT20 raw candidate count/identity/order = 100% canonical parity;
- entry price and frozen geometry parity = 100%;
- phantom/duplicate timing tests PASS;
- generated-entry B27DV pooled-major arbitration reproduces 283 accepted in exact order.

Otherwise status is `B27DW_RAW_5M_SIGNAL_PARITY_NOT_READY` and mismatches are persisted.

Even a PASS is forward-shadow readiness only. It does not enable real-money exchange entry writes.
