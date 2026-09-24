# BNB B42-S1 — 1% Opportunity Atlas Preregistration

## Objective

Measure the true supply of causal BNBUSDT ±1% / RR 1:1 opportunities before trying to discover a strategy.

This stage answers:

> Does BNB actually present at least one 1% first-touch opportunity per day often enough to justify a target of ~1 trade/day?

No indicator/rule selection, ML threshold, WR optimization, leverage, fee tuning, or strategy promotion is allowed in S1.

## Data

- Binance USD-M BNBUSDT 5m monthly archive.
- Observation period: 2022-01-01 00:00 UTC through 2026-08-26 00:00 UTC.
- Minimum normalized 5m coverage: 99.5%.
- OHLCV retained.
- Decision timestamps: every completed 15m boundary derived from 5m data.

## Causal entry

At completed decision bar t:

- no future data are used for the decision timestamp;
- entry is the **next 5m bar open**;
- both LONG and SHORT hypothetical directions are labeled independently;
- maximum holding window = 12 hours = 144 future 5m bars.

## Frozen barriers

LONG:
- TP = entry × 1.01
- SL = entry × 0.99

SHORT:
- TP = entry × 0.99
- SL = entry × 1.01

RR = 1:1 before costs.

## First-touch outcome

For each direction:

- WIN: TP is first touched before SL.
- LOSS: SL is first touched before TP.
- AMBIGUOUS: TP and SL are both first touched in the same 5m candle.
- TIMEOUT: neither barrier is touched within 12h.

AMBIGUOUS observations are never resolved in favor of the strategy.

For opportunity-existence statistics, only WIN counts as a successful 1% opportunity.

## Reporting

Report:
- total decision timestamps;
- total directional candidates;
- WIN/LOSS/TIMEOUT/AMBIGUOUS counts and rates;
- side-specific rates;
- year-specific rates;
- unique UTC days;
- percentage of UTC days with >=1 WIN opportunity;
- percentage with >=1 LONG WIN;
- percentage with >=1 SHORT WIN;
- median / Q25 / Q75 number of WIN opportunities per day;
- percentage of days with >=5 and >=10 WIN candidates;
- same metrics for DEV 2022-2024 and REF 2025-2026.

## S1 feasibility gate

Opportunity supply is **SUFFICIENT_FOR_DISCOVERY** only if all hold:

1. all-period days with >=1 WIN >= 95%;
2. DEV days with >=1 WIN >= 95%;
3. REF days with >=1 WIN >= 90%;
4. median WIN opportunities/day >= 5.

Otherwise:
`BNB_B42_S1_OPPORTUNITY_SUPPLY_INSUFFICIENT`.

If passed:
`BNB_B42_S1_OPPORTUNITY_ATLAS_READY`.

Passing does NOT imply a tradable 80% WR strategy exists. It only proves the market supplies the movement.

## Framework

B42 research environment pins `vectorbt==1.1.0`, the current stable release selected before S1 outcomes are observed. S1's barrier labeling remains explicit/custom to preserve exact first-touch semantics; vectorbt is introduced for downstream feature/portfolio discovery.
