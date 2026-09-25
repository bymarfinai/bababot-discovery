# BNB B42 — Stop Verdict after S4

## Final status

**BNB_B42_STOP_NO_DISCOVERY_EDGE_FOR_1PCT_DAILY_SELECTOR**

The B42 lineage is stopped after S4 under its preregistered stop rule.

## What was established

### S1 — Opportunity supply
Status: `BNB_B42_S1_OPPORTUNITY_ATLAS_READY`

- 1699 UTC days, 2022-01-01 through 2026-08-26.
- 98.76% of days contained at least one causal next-5m-open candidate that reached +1% before -1% within 12h.
- Movement supply is therefore not the bottleneck.

### S2 — Generic OHLCV / indicator selector
Status: `BNB_B42_S2_SELECTOR_CALIBRATION_NOT_READY`

- 2024 calibration: ~0.962 trades/day, WR 45.17%.
- 2025-2026 descriptive REF: ~0.837 trades/day, WR 44.16%.
- Generic price/volume/indicator features did not identify the daily +1% winner.

### S3 — Turning-point location gates
Status: `BNB_B42_S3_NO_ROBUST_TURNING_POINT_EVENT`

- Q80 wall reclaim/reject, causal swing sweeps, prior-24h extreme sweeps, and >=2-concept confluence all failed robust DEV/REF gates.
- Confluence did not rescue event quality.

### S4 — Historical derivatives information
Status: `BNB_B42_S4_NO_DERIVATIVES_DISCRIMINATORY_EDGE`

Official Binance USD-M archive coverage:
- metrics: 1711/1711 daily files, 492,631 rows;
- premium index 15m: 163,872 rows;
- funding: 5,205 rows.

Eligible features included:
- OI level/change/value change;
- global long-short account ratio;
- premium level/z-score/change and directional forms;
- realized funding and directional funding.

None reached the frozen nomination requirement (DEV AUC >=0.58, REF >=0.55, >=4/5 years >=0.53).

Best stable-looking REF values remained near random:
- directional premium z7d: DEV 0.501 / REF 0.516;
- directional global account ratio: DEV 0.518 / REF 0.513;
- funding: DEV 0.507 / REF 0.509.

## Stop rule

Do not execute B42-S5 combined selector, S6 validation, or S7 economics using the same B42 information set.

Do not rescue by:
- hyperoptimizing thresholds;
- adding arbitrary indicator combinations;
- reweighting the same derivatives fields;
- selecting REF-favorable subsets;
- changing TP/SL after seeing these outcomes.

## What would justify a new lineage

Only a materially different information source / selection problem, for example:
- genuine historical options-IV surface / expected HOD-LOD information;
- historical liquidation-event/order-book data with sufficient causal coverage;
- another independently justified microstructure source not already encoded in OHLCV/taker/metrics/premium/funding.

B42 should remain frozen as evidence that BNB has ample +1% movement, but the tested public candle/positioning information does not reliably tell which one candidate per day will win.
