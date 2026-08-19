# BTC Friday SR80 — Support/Resistance Level Reliability Preregistration

**FROZEN BEFORE RESULT. Research-only; live BBC untouched.**

## Objective
Test whether a causal BTCUSDT support/resistance level can be classified as high-confidence **before its reaction is known**, with observed first-touch hold/rejection rate >=80% on both discovery and chronological validation.

This is NOT a trading-strategy backtest. Primary target is level correctness: does the level act as support/resistance when first touched?

## Data / chronology
- BTCUSDT USD-M perpetual, official Binance Data Vision 5m data.
- Historical window aligned to existing Friday research: 2023-12-02 through 2026-07-30 exclusive, with prior warmup as available.
- Friday is defined in **Asia/Jakarta (WIB)**, 00:00 through 23:59.
- Each Friday's candidate levels are frozen at Friday 00:00 WIB. No level formed later that Friday is allowed.
- Split by unique Friday-WIB date: first 70% discovery, last 30% validation.

## Frozen candidate-level families
At Friday 00:00 WIB, generate only these causal price levels from completed history:
1. previous-WIB-day high (`PDH`)
2. previous-WIB-day low (`PDL`)
3. prior-7-WIB-day high (`W7H`)
4. prior-7-WIB-day low (`W7L`)
5. up to three most recent confirmed 1H swing highs from the prior 7 days (`SWING_H`)
6. up to three most recent confirmed 1H swing lows from the prior 7 days (`SWING_L`)

1H swing definition is fixed: centered pivot with 3 completed 1H bars on each side. Because all pivots are generated before Friday starts, right-side confirmation is fully causal.

Nearby raw levels within **0.10 x Friday-start ATR14(1H)** are clustered. Cluster price is the median member price. This prevents double-counting nearly identical levels. Cluster features retain source-family membership and confluence count.

At Friday start:
- cluster below Friday-open = SUPPORT
- cluster above Friday-open = RESISTANCE
- exact equality is excluded.

## First touch
For each frozen cluster, find its first 5m candle during that Friday whose high-low range contains the cluster price.
No later touch is used.

A level is eligible for outcome scoring only when the first-touch candle does NOT itself make outcome ordering unknowable.

## Frozen correctness label
Reference scale = Friday-start ATR14 from completed 1H bars.
Reaction distance = **0.50 ATR** symmetrically.
Outcome horizon = **6 hours after first touch**.

SUPPORT:
- `HOLD` if price reaches `level + 0.50 ATR` before reaching `level - 0.50 ATR`.
- `BREAK` if `level - 0.50 ATR` is reached first.

RESISTANCE:
- `HOLD` if price reaches `level - 0.50 ATR` before reaching `level + 0.50 ATR`.
- `BREAK` if `level + 0.50 ATR` is reached first.

If the touch candle itself reaches either boundary, or any later 5m candle reaches both boundaries, label `AMBIGUOUS` and exclude from WR. If neither boundary is reached inside 6h, label `UNRESOLVED` and exclude from WR.

Primary correctness metric = HOLD / (HOLD + BREAK).

## Frozen pre-reaction feature set
All features are available before the reaction outcome is known. Touch-time features use only completed 5m bars strictly before the first-touch candle.

Level provenance / structure:
- support vs resistance
- has previous-day source
- has prior-7d extreme source
- has confirmed-swing source
- confluence count
- distance from Friday open in ATR
- prior-7d near-touch count within 0.10 ATR
- level age in hours (youngest source)

Approach state before touch:
- signed 30m return toward the level
- signed 60m return toward the level
- 30m high-low range / ATR
- fraction of prior six 5m candles moving toward the level
- 30m quote-volume / trailing prior-24h 30m median quote-volume
- side-aligned completed EMA20 1H slope over prior 3h
- ATR / price

No post-touch candle geometry, no touch-candle close, no funding/OI, and no outcome-derived features.

## Frozen selector
One `sklearn.tree.DecisionTreeClassifier` only:
- criterion = `gini`
- max_depth = 3
- min_samples_leaf = 20
- random_state = 20260819
- no class weights
- discovery-median imputation only
- no hyperparameter sweep

Training label: HOLD=1, BREAK=0 on discovery resolved observations only.

Candidate high-confidence leaf must have discovery:
- N >= 30 resolved first touches
- empirical HOLD rate >= 80%
- predicted class HOLD

If multiple candidate leaves exist, select exactly one by:
1. highest discovery HOLD rate
2. largest N
3. smallest numeric leaf id

Only this exact frozen leaf is evaluated on validation.

## SR80 promotion gates
Verdict `BTC_FRIDAY_SR80_CANDIDATE` only if ALL are true:
1. discovery resolved N >= 30 and HOLD rate >=80%
2. validation resolved N >= 12 and HOLD rate >=80%
3. combined resolved N >= 50 and HOLD rate >=80%
4. validation HOLD rate exceeds unconditional validation level HOLD rate
5. selected observations include at least 2 distinct level-source families OR confluence rule explicitly selects multi-source clusters
6. at least 3/4 chronological full-history blocks containing >=5 selected resolved levels have HOLD rate >50%
7. zero causality/integrity violations

Otherwise verdict `REJECT_SR80_LEVEL_IDENTIFIER`.

Report Wilson 95% confidence interval for discovery, validation and full selected HOLD rates as uncertainty context. The Wilson lower bound is descriptive, not an additional promotion gate.

## Guardrails
- No reaction-distance sweep after result.
- No changing 0.10 ATR clustering/touch tolerance after result.
- No alternate pivot span after result.
- No deeper tree, smaller leaf, new feature, hour filter, support-only/resistance-only rescue, or runner-up validation after result.
- No TP/SL/PnL interpretation at SR80 stage.
- If SR80 passes, freeze the exact level definition + leaf and transfer unchanged to ETH/SOL/BNB before any live use.
- Observed 80% historical HOLD rate is not a guarantee of future behavior.
