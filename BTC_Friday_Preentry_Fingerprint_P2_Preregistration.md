# BTC Friday Pre-entry Fingerprint P2 — Shallow Price/Candle Tree

**FROZEN BEFORE RESULT. Research-only; live BBC untouched.**

## Objective
Identify one human-readable BTC Friday pre-entry price/candle state whose canonical executable trade has observed WR >=80%, then (only if it qualifies) freeze and transfer it unchanged to other pairs.

## Canonical outcome
BTCUSDT Friday 08:00 UTC LONG, entry 08:00 5m open, TP +2.00%, SL -0.70%, max hold 360m, $500 notional, 0.15% round-trip cost, adverse-first dual touch. Same parent simulator as F5.17/P0/P1.

## Causal information set
All features are computed strictly from completed bars before entry T plus the executable entry open at T where explicitly stated.

Price/candle-only frozen features:
- F6.37 last-5m continuous geometry: body, upper wick, lower wick, upper-minus-lower, upper-vs-prior3 median, body-vs-prior3 median, upper-share-vs-prior3 median;
- completed last-15m aggregate: return, body ratio, upper-wick ratio, lower-wick ratio, close location in range, range/open;
- completed last-1h aggregate: same six features;
- completed 4h return;
- entry-open distance to completed 5m EMA7 and EMA20;
- completed EMA7 and EMA20 15m slopes.

No volume, taker flow, funding, OI, time-of-day alternative, or post-entry information.

## Model
Exactly one `sklearn.tree.DecisionTreeClassifier`:
- criterion=`gini`
- max_depth=2
- min_samples_leaf=12
- random_state=20260819
- no class weights
- no hyperparameter sweep

Training = canonical discovery first 82 Fridays only. Validation last 56 Fridays is never used to fit tree or choose thresholds.

## Candidate leaf selection
After fitting on discovery, consider positive-prediction leaves with discovery N>=12 and empirical WR>=80%. If multiple exist, choose exactly one by:
1. highest discovery WR;
2. largest N;
3. smallest numeric leaf id.

The exact root-to-leaf inequalities become the human-readable candle fingerprint.

## 80% promotion gates
`BTC_FRIDAY_80_CANDIDATE` only if selected leaf:
- discovery N>=12 and WR>=80%;
- validation N>=8 and WR>=80%;
- combined N>=20 and WR>=80%;
- validation expectancy >0 and PF>1;
- validation WR > unconditional validation WR;
- at least 3/4 full-history chronological blocks containing selected trades have positive PnL.

Otherwise `REJECT_P2_80_CANDLE_IDENTIFIER`.

## Guardrail
Observed WR is not a guarantee. No tree depth/min-leaf/feature/threshold/TP-SL tuning after seeing P2. If P2 fails, do not try a deeper tree on the same feature set merely to force 80%.