# BNB B43-S2 — Forward IV HOD/LOD Validation Preregistration

## Objective

Prospectively test whether B43-S1 live BNB options-IV expected-move levels identify future BNB high/low zones better than chance-like distance alone.

This stage evaluates **frozen levels before future price action**. It is not yet a trading strategy.

## Parent

- B43-S1 status: `BNB_B43_S1_LIVE_IV_LEVEL_MAP_READY`
- S1 signature: `639567dd76cd129cb0085c7c29d7f9a7e00ae4c0fc2b59a58cad270871212211`
- Formula: `EM = S × average(call Ask IV, put Ask IV) × sqrt(T_years)`
- ATM rule: nearest strike to index with valid positive CALL + PUT Ask IV.

The first S1 snapshot at 2026-09-25T02:16:27.689Z is prototype evidence and is **not promotion-eligible** for S2 because S2 rules were not yet frozen.

## Snapshot cadence

- BNBUSDT only.
- Capture one exact live snapshot every hour.
- Each snapshot stores:
  - Binance options exchange serverTime;
  - BNB options index;
  - valid BNB symbols/expiries needed by the frozen ATM rule;
  - CALL/PUT Ask IV and Mark IV;
  - projected +/-0.5 sigma and +/-1 sigma levels for each valid expiry.

No stale-IV substitution.

## Primary expiry buckets

At each snapshot, map live expiries to:

- **D0** = nearest expiry with >6h remaining.
- **D1** = expiry closest to 1 day remaining, with >6h preferred.
- **W1** = expiry closest to 7 days remaining.

If D0 and D1 resolve to the same contract, keep both labels but de-duplicate identical levels in headline counts.

Primary evaluation uses Ask-IV levels only. Mark-IV levels are diagnostic.

## Frozen forward horizons

Every snapshot is evaluated at:

- +1 hour
- +4 hours
- +24 hours

A horizon is COMPLETE only when all required BNBUSDT 5m bars are available.

## Frozen level families

Per expiry bucket:

- LOWER_0_5SIGMA
- UPPER_0_5SIGMA
- LOWER_1SIGMA
- UPPER_1SIGMA

LOWER = candidate LOD/support zone.
UPPER = candidate HOD/resistance zone.

## Capture error

For horizon H after snapshot time T:

- upper actual extreme = maximum 5m high in (T, T+H]
- lower actual extreme = minimum 5m low in (T, T+H]

For UPPER level L:
`capture_error_bps = abs(actual_high - L) / L × 10,000`

For LOWER level L:
`capture_error_bps = abs(actual_low - L) / L × 10,000`

Report capture bands:
- <=25 bps
- <=50 bps
- <=100 bps
- <=150 bps

No threshold is tuned after outcomes.

## Touch + reaction

A level is touched if any completed 5m bar in the evaluation horizon satisfies:
`low <= L <= high`.

For the first touched bar, evaluate the following completed bars up to 30 minutes or horizon end.

UPPER:
- penetration = max(0, post-touch max high - L)
- favorable reaction = max(0, L - post-touch min low)
- rejected close = final close < L

LOWER:
- penetration = max(0, L - post-touch min low)
- favorable reaction = max(0, post-touch max high - L)
- rejected close = final close > L

Distances are converted to bps of L.

Frozen reaction labels:
- STRONG_REACTION_30:
  favorable >=50 bps AND favorable >=1.5×penetration AND rejected close.
- CLEAN_REACTION_30:
  favorable >=25 bps AND favorable > penetration AND rejected close.
- BREAK_THROUGH_30:
  penetration >=50 bps AND penetration > favorable AND not rejected close.
- otherwise MIXED_30.
- untouched = NOT_TOUCHED.

## Daily HOD/LOD headline

For each UTC day, use the **first promotion-eligible snapshot taken at or after 00:00 UTC and before 01:00 UTC** as the canonical daily map when available.

For that daily map, evaluate through 23:59:59 UTC:
- distance of D1/W1 UPPER levels to actual UTC-day high;
- distance of D1/W1 LOWER levels to actual UTC-day low.

Hourly snapshots remain useful for path/reaction anatomy but do not multiply the daily HOD/LOD sample.

## Promotion gates

No B43 mechanism verdict until both sample gates are met:

### Hourly path gate
- >=100 promotion-eligible hourly snapshots with complete +4h evaluation.

### Daily HOD/LOD gate
- >=30 canonical UTC-day maps with complete daily evaluation.

Then B43-S2 is supported only if ALL:

1. **Daily capture**
   - at least one primary Ask-IV upper level (D1 or W1, 0.5σ or 1σ) is within 100 bps of actual daily high on >=60% of canonical days;
   - at least one primary Ask-IV lower level is within 100 bps of actual daily low on >=60% of canonical days.

2. **Hourly reaction**
   - among touched primary levels in +4h windows, CLEAN_REACTION_30 or STRONG_REACTION_30 >=60%;
   - BREAK_THROUGH_30 <=25%.

3. **Stability**
   - no calendar month with >=10 canonical days may have both upper and lower <=100 bps capture rates below 40%.

Status before sample gate:
`BNB_B43_S2_FORWARD_ACCUMULATING`

Sample reached + quality pass:
`BNB_B43_S2_IV_HOD_LOD_MECHANISM_SUPPORTED`

Sample reached + quality fail:
`BNB_B43_S2_IV_HOD_LOD_NOT_SUPPORTED`

Even a pass does not create a trading strategy. Entry/TP/SL would be B43-S3+.
