# BNB B34-S1 — Derivatives-Confirmed Liquidity Sweep Preregistration

**Scientific identity:** `BNB_B34_S1_DERIVATIVE_CONTEXT_V1`

## Parent
Frozen parent: B33 strongest near-miss only:
- detector: `F1LE = LIQUIDITY_SWEEP_LONG_EARLY`
- entry: `E1 = NATIVE_LEVEL_RETEST`
- side: LONG only
- development parent evidence: N=3,014, +60 directional hit=54.0478%
- parent entry timestamps and signed +30/+60/+120 outcomes are read only from the persisted B33-S2 entry ledger.

B33 structure and entry logic may not be changed.

## New hypothesis
A causal LONG liquidity-sweep retest becomes actionable only when derivatives positioning confirms that new exposure and aggressive flow are supporting the move.

This is a new information source, not an OHLC reslice.

## New causal data
Official Binance Futures Data Vision `BNBUSDT` metrics, aligned strictly before the frozen entry timestamp:
- `sum_open_interest_value`
- `sum_taker_long_short_vol_ratio`
- `sum_toptrader_long_short_ratio`
- `count_long_short_ratio`

Maximum metric staleness: 10 minutes.
OI change uses a metric observation at least 60 minutes earlier, also strictly pre-entry.

## Frozen gate family
No learned thresholds and no tree/model search.

- `G0_BASELINE`: no derivatives filter; diagnostic only.
- `G1_OI_EXPANSION`: OI value 60m log-change > 0.
- `G2_OI_TAKER_CONFIRM`: G1 AND taker long/short volume ratio > 1.0.
- `G3_OI_TAKER_SMART_CONFIRM`: G2 AND top-trader position long/short ratio > global account long/short ratio.

At most one of G1-G3 may be selected.

## Outcome
Directional signed close-to-close outcomes are inherited from B33 at +30m, +60m, +120m.
This stage does not simulate TP, SL, PnL, fees, leverage, sizing, MFE/MAE or DD.

## Development
Years: 2022, 2023, 2024.

A derivatives gate passes only if:
1. aligned N >= 300;
2. each year N >= 75;
3. participation >= 10% of aligned G0 parent;
4. pooled +60 hit >= 56%;
5. Wilson 95% LCB > 53%;
6. every development-year +60 hit >= 53%;
7. improvement versus aligned G0 +60 hit >= 1.5 percentage points;
8. at least one of +30/+120 hit >= 55%.

Ranking among passers:
1. highest worst-year +60 hit;
2. highest Wilson LCB;
3. highest pooled +60 hit;
4. largest N;
5. lexical gate id.

If no gate passes, stop B34-S1 and do not open reference.

## One-shot reference
Only the single frozen development winner may open 2025-2026 reference.

Reference pass:
1. N >= 100;
2. 2025 N >= 50;
3. 2026 N >= 25;
4. participation >= 10% of aligned reference G0;
5. pooled +60 hit >= 54%;
6. Wilson 95% LCB > 51%;
7. each reference year +60 hit > 51%;
8. improvement versus aligned reference G0 >= 1.0 percentage point;
9. at least one of +30/+120 hit >= 53%.

## Anti-rescue
- no new OHLC structure;
- no new entry trigger;
- no threshold tuning;
- no percentile optimization;
- no session/hour/day filter;
- no post-result derivatives feature addition;
- no reference inspection without a development passer;
- no economics unless the one-shot reference passes.

## Promotion
Only `BNB_B34_S1_DERIVATIVE_CONTEXT_PASS` may advance to an economics stage.
