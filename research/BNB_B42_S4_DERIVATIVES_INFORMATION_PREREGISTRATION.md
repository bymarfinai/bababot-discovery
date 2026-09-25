# BNB B42-S4 — Historical Derivatives Information Audit & Discrimination Preregistration

## Objective

Test whether causal derivatives/positioning information adds genuinely new information for the frozen B42-S1 +1%/-1% opportunity labels.

This is S4 of B42. It is not a trading strategy and does not select one trade/day yet.

Frozen parents:
- B42-S1 signature: `ce5dcd0bdb095d6aa9ea8991e851e44c9f21fb898d36ff9848cb5884ef9a14fd`
- B42-S2 generic OHLCV selector failed.
- B42-S3 location/turning-point gates failed.

## Official data sources

Only official Binance USD-M public archives:
1. daily `metrics/BNBUSDT`
2. monthly `premiumIndexKlines/BNBUSDT/15m`
3. monthly `fundingRate/BNBUSDT`

No reconstructed OI from price, no vendor data, no future-filled ratios.

## S4A coverage gate

For each archive family:
- inspect actual CSV schema;
- normalize timestamps;
- verify monotonicity/duplicates;
- report earliest/latest timestamp;
- calculate candidate alignment coverage against B42-S1 decision timestamps.

A derivatives feature is allowed into S4B only if:
- its source timestamp is <= decision timestamp;
- all rolling inputs are completed before or at decision time;
- DEV 2022-2024 aligned coverage >=90%;
- REF 2025-2026 aligned coverage >=90%.

Funding may align sparsely because it updates at funding times; latest realized funding <= t can be carried forward for context if age <=24h.

## Frozen candidate target

Use B42-S1 directional candidates unchanged.

Binary outcome:
- positive = WIN
- negative = LOSS / TIMEOUT / AMBIGUOUS

No outcome-derived features.

## Frozen feature families

### Open interest / metrics
Use fields only if present in the official metrics schema:
- oi_level_log = log(sum_open_interest)
- oi_change_15m
- oi_change_60m
- oi_change_240m
- oi_value_change_60m
- oi_value_change_240m

### Position ratios
If present:
- global_account_log_ratio = log(count_long_short_ratio)
- top_account_log_ratio = log(count_toptrader_long_short_ratio)
- top_position_log_ratio = log(sum_toptrader_long_short_ratio)

Directional versions multiply log-ratio by +1 for LONG and -1 for SHORT.

### Taker positioning
If present:
- taker_log_ratio = log(sum_taker_long_short_vol_ratio)
- directional_taker_log_ratio = taker_log_ratio × direction
- taker_change_60m

This is included as a control because taker-flow has prior repo coverage; it is not treated as a novel standalone discovery.

### Premium / basis proxy
Using completed 15m premium-index close:
- premium_close
- premium_z_7d using prior 7d completed bars, current bar excluded from reference
- premium_change_60m
- directional_premium
- directional_premium_z_7d
- directional_premium_change_60m

### Funding
Using latest realized funding row with fundingTime <= decision timestamp and age <=24h:
- latest_funding
- funding_age_hours
- directional_funding

## Frozen discrimination test

For each eligible feature:
- calculate ROC AUC on DEV 2022-2024 and REF 2025-2026;
- orientation is chosen on DEV only:
  - if DEV AUC < 0.5, multiply feature by -1;
- report oriented DEV AUC and REF AUC;
- report median feature for WIN and non-WIN;
- report year-specific oriented AUC for 2022, 2023, 2024, 2025, 2026.

No threshold search and no classifier in S4.

## Nomination gate

A feature is nominated only if ALL:
- DEV usable N >=50,000 directional candidates;
- REF usable N >=25,000;
- DEV oriented AUC >=0.58;
- REF oriented AUC >=0.55;
- at least 4/5 calendar years oriented AUC >=0.53;
- DEV and REF orientation are consistent (REF raw direction agrees with DEV orientation, i.e. oriented REF AUC >=0.50).

A feature-family can advance if >=1 member is nominated.

Status:
- >=1 nominated feature: `BNB_B42_S4_DERIVATIVES_INFORMATION_READY`
- coverage passes but none nominated: `BNB_B42_S4_NO_DERIVATIVES_DISCRIMINATORY_EDGE`
- insufficient archive coverage: `BNB_B42_S4_DERIVATIVES_HISTORY_INSUFFICIENT`

## Stop rule

If S4 status is not `...INFORMATION_READY`, do not force B42-S5 by hyperoptimizing thresholds on these same derivatives features.
