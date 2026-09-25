# BNB B43-S1 — Options-IV HOD/LOD Level Map Specification

## Objective

Start a new BNB research lineage using an information family materially different from B42:

`BNB options implied volatility -> projected expected-move levels -> future HOD/LOD reaction`.

This stage is a **feasibility + level-map construction stage**, not a trading-performance test.

## Why B43 exists

B42 established that:
- +1% movement supply exists on 98.76% of days;
- generic OHLCV/indicator selection failed;
- Q80/sweep/location gates failed;
- OI/long-short/premium/funding features were near-random discriminators.

B43 therefore does not reuse those features as its primary signal source.

## Historical-access finding before performance testing

1. Binance announced additional BNBUSDT Daily Options from 2023-08-30.
2. The live Options API exposes current BNB option chain, askIV/markIV/Greeks, and option klines for currently valid symbols.
3. Direct tests against expired BNB option symbols, including a contract that expired one day earlier, returned:
   `The symbol is either in PENDING_TRADING status or does not exist.`
4. Historical-exercise probes for BNB returned no usable chain history for the tested windows.
5. Binance's public bulk-data repository documents spot/usd-m/coin-m archive families; no equivalent official bulk options-IV archive was identified.
6. Prior GitHub-hosted direct EAPI collection in this repo hit HTTP 451.

Therefore B43-S1 does **not** fabricate historical askIV. Historical exact replay remains unavailable from the tested official paths.

## Frozen live level-map formula

Observation timestamp = Binance Options exchange `serverTime`.

Underlying anchor:
- `S = BNBUSDT options index price`.

For each live expiry:
1. enumerate BNBUSDT option symbols;
2. sort strikes by absolute distance to S;
3. select the nearest strike K for which both CALL and PUT exist and both have finite positive `askIV`;
4. define:
   - `IV_ask = (call.askIV + put.askIV) / 2`
   - `IV_mark = (call.markIV + put.markIV) / 2`
5. time to expiry:
   - `T = max(expiry_ms - observation_ms, 0) / (365 * 86400000)`
6. conventional annualized-volatility expected move hypothesis:
   - `EM_ask = S * IV_ask * sqrt(T)`
   - `EM_mark = S * IV_mark * sqrt(T)`
7. project:
   - `Upper_0.5σ = S + 0.5 * EM_ask`
   - `Lower_0.5σ = S - 0.5 * EM_ask`
   - `Upper_1σ = S + EM_ask`
   - `Lower_1σ = S - EM_ask`

This is a conventional expected-move hypothesis only. It is **not claimed to reproduce the proprietary formulas visible in the reference video**.

## Causality

All fields in each snapshot must be captured at one observation timestamp before any future evaluation period.

No future high/low may influence:
- ATM strike selection;
- IV;
- expiry selection;
- band computation.

## S1 status

If:
- live BNB chain is available;
- >=3 expiries have valid call+put askIV pairs;
- all calculated bands are finite and ordered;

then:

`BNB_B43_S1_LIVE_IV_LEVEL_MAP_READY`

Otherwise:

`BNB_B43_S1_LIVE_IV_LEVEL_MAP_NOT_READY`

## Next research gate

B43-S2 may only test **future** price reaction to already-frozen snapshots, or use a genuinely independent historical options source discovered later.

No synthetic "historical askIV" may be backfilled from future information and presented as exact Binance askIV.
