# SOL Options Liquidity Map V1 — Preregistration

## Purpose

Build a prospective, causal options-derived price map for SOL and attach it to the already-frozen SOL structural detector.

This is **not** a new entry rule and **not** a claim that the strategy shown in the reference video has been replicated.

V1 answers only:

1. where current SOL option positioning is concentrated;
2. where option-implied volatility places near-term statistical price bands;
3. whether those independent levels cluster near the same prices;
4. how to capture the chain prospectively so later SOL setups can be tested without hindsight.

The existing SOL detector is unchanged.

## Data source

Official Binance Options public market data only:

- Exchange information: `GET /eapi/v1/exchangeInfo`
- Underlying index: `GET /eapi/v1/index?underlying=SOLUSDT`
- Option mark/Greeks: `GET /eapi/v1/mark`
- Open interest by expiry: `GET /eapi/v1/openInterest?underlyingAsset=SOL&expiration=YYMMDD`

No futures OI, funding, long/short ratio, taker ratio, or liquidation fields are mixed into this map.

## Universe

At each snapshot:

- Underlying: SOLUSDT.
- Use contracts whose symbol starts with `SOL-`.
- Use the **three nearest distinct expiries** that are still unexpired at the snapshot time.
- Calls and puts are treated separately.
- Contract rows require a valid strike, non-negative gamma, positive mark IV, and available OI.
- Invalid sentinel IV values (e.g. -1) are not used in IV calculations.

Expiry time is read from exchangeInfo where available. Symbol-date parsing is fallback only.

## Important terminology

`gamma * OI` is called **gamma concentration magnitude**.

It is **not** called dealer GEX because public chain data does not identify whether dealers are net long or short each option.

V1 therefore does not infer dealer hedging direction.

## Frozen calculations

### 1. Spot

`spot = SOLUSDT options index price`.

### 2. Per-contract gamma concentration

For each option:

`gamma_concentration = abs(gamma) * sumOpenInterest`

This is a magnitude-only concentration measure.

### 3. Per-expiry normalized concentration

Within each expiry and option side separately:

`oi_share = contract_OI / total_side_OI`

`gamma_share = gamma_concentration / total_side_gamma_concentration`

If a denominator is zero, the corresponding share is zero.

### 4. Cross-expiry strike concentration

For each strike, aggregate the three nearest expiries by **equal-weight mean** of:

- OI share;
- gamma share.

No DTE optimization or fitted expiry weighting is allowed in V1.

`concentration_score = 0.5 * mean_oi_share + 0.5 * mean_gamma_share`

Calls above spot form the upper map.
Puts below spot form the lower map.

The top three strikes on each side by concentration score are reported as descriptive walls.

No minimum score threshold is promoted in V1.

### 5. ATM IV expected move

For each of the three expiries:

- identify the strike closest to spot with both call and put rows when possible;
- ATM mark IV = mean of valid call and put mark IV at that strike;
- fallback: nearest valid option mark IV pair/row if a complete pair is unavailable.

Time to expiry is measured from snapshot timestamp to expiry timestamp.

`expected_move = spot * ATM_IV * sqrt(T_years)`

`iv_floor = spot - expected_move`

`iv_ceiling = spot + expected_move`

These are statistical IV bands, not guaranteed support/resistance.

### 6. Confluence distance

For every upper/lower concentration strike, compute its absolute percentage distance from every IV floor/ceiling on the same side.

Report the nearest IV-band distance.

A level is labeled `IV_CONFLUENT` descriptively if nearest distance <= **1.00% of spot**.

This 1% threshold is frozen before the first V1 map is calculated and is not a trading gate.

### 7. Map outputs

Each snapshot must contain:

- snapshot timestamp;
- SOL index spot;
- expiries used;
- raw chain rows;
- OI rows;
- per-expiry ATM IV and IV floor/ceiling;
- top three lower put-concentration strikes;
- top three upper call-concentration strikes;
- concentration scores;
- nearest IV-band distance;
- descriptive confluence label.

## Prospective storage

Every captured snapshot receives:

- `map_version = SOL_OPTIONS_LIQUIDITY_MAP_V1`;
- `snapshot_id`;
- server/source timestamp;
- complete raw and derived JSON payload.

Snapshots are append-only.

Later outcome studies must align a SOL detector event only to the latest options snapshot whose timestamp is **<= detector decision timestamp**.

Never use a later snapshot for an earlier setup.

## Prospective validation plan

V1 itself does **not** promote a trade filter.

After sufficient prospective samples exist, a separately preregistered study may test whether:

- detector setups occurring near V1 lower/upper concentration levels have higher structural-event rate;
- IV-confluent levels improve winner rate or realized R;
- distance to concentration walls explains Missing-B or other residual failures.

No threshold may be tuned from the same validation sample.

## V1 current-map status

The first map is descriptive only because it is the first prospective snapshot.

Allowed status:
- `OPTIONS_MAP_CAPTURE_READY`
- `OPTIONS_MAP_DATA_INSUFFICIENT`
- `OPTIONS_MAP_FETCH_ERROR`

No `validated`, `robust`, or `ready-to-trade` label is allowed from V1 alone.
