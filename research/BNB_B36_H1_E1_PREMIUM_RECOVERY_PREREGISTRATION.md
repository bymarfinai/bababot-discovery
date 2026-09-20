# BNB B36 — 1H Sweep + Premium Recovery Confirmation Preregistration

**Scientific identity:** `BNB_B36_H1_E1_PREMIUM_RECOVERY_V1`

## Frozen parent
B35 is frozen and rejected under its preregistered development gate. B36 does not alter B35.

Parent is the single strongest B35 development entry:
- structure: `H1_SWING_LOW_SWEEP_RECLAIM_LONG`
- entry: `E1_NATIVE_LEVEL_RETEST`
- side: LONG
- B35 development: N=805; +120 hit=55.4037%; Wilson LCB=51.9524%
- B35 reference 2025-2026 remained unopened.

Choosing this parent is explicitly post-B35 and therefore B36 is a **new exploratory identity with a new information source**, not a claim that B35 passed.

## New information source
Official Binance USD-M `BNBUSDT` 15m Premium Index Klines.

For each frozen B35 E1 entry:
1. use the latest fully completed premium-index bar whose close timestamp is **strictly before** entry;
2. maximum staleness: 30 minutes;
3. trailing reference = previous 7 calendar days of completed 15m premium closes, excluding the current premium bar;
4. require >=192 prior observations;
5. `premium_z = (current premium close - prior7d_mean) / prior7d_std`;
6. `premium_delta_60 = current premium close - premium close approximately 60m earlier`, requiring prior age 45-75m.

No B35 OHLC structure or entry timestamp is recomputed or changed.

## Frozen tests
- `P0_ALIGNED_BASELINE`: all causally premium-aligned parent entries; descriptive only.
- `P1_NEGATIVE_PREMIUM`: premium_z < 0; descriptive only.
- `P2_NEGATIVE_RECOVERING`: premium_z < 0 AND premium_delta_60 > 0; **the only promotion-eligible hypothesis**.

There is no magnitude threshold, sigma sweep, lookback sweep, or gate selection.

## Development
2022-2024 only.

P2 may open reference only if ALL:
1. N >=160;
2. each development year N >=40;
3. participation >=20% of aligned P0;
4. pooled +120 hit >=57%;
5. Wilson 95% LCB >53%;
6. every development-year +120 hit >=53%;
7. median signed +120 >0;
8. improvement over aligned P0 +120 >=1.5 percentage points;
9. at least one of +60/+240 hit >=54%.

P1 cannot be promoted regardless of result.

## One-shot reference
Only if P2 passes development, open B35's previously unopened 2025-2026 parent observations with the identical premium rule.

Reference pass:
1. N >=80;
2. 2025 N >=40;
3. 2026 N >=20;
4. participation >=20% of aligned reference P0;
5. pooled +120 hit >=54%;
6. Wilson 95% LCB >51%;
7. 2025 and 2026 each >51%;
8. median signed +120 >0;
9. improvement over aligned reference P0 >=1.0 percentage point;
10. at least one of +60/+240 hit >=53%.

## Anti-rescue
- no B35 structure or entry edits;
- no premium-z magnitude threshold added later;
- no alternate premium lookback;
- no funding/OI/taker filter added to B36;
- no clock/session/day filter;
- no lower gate;
- P1 cannot rescue P2;
- no reference inspection if P2 development fails;
- no economics unless reference passes.
