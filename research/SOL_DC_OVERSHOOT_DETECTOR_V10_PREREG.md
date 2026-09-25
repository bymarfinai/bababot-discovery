# SOL DC Overshoot Detector V10 — Preregistration

## Purpose
Convert the V9 stable overshoot anatomy into a causal detector and test whether it produces an executable SOL LONG edge.

## Frozen parent event
- Directional Change upturn confirmation, theta 0.50%.
- Eligible only when causal NEW_LONG_BUILD context is active.
- Signal at completed 15m confirmation close.
- Entry = next 15m open.

## Targets
V9 passed anatomy gate for:
- OS2 = +2% overshoot before next DC downturn confirmation.
- OS3 = +3% overshoot before next DC downturn confirmation.

## Frozen V9 feature sets
Duplicates/aliases are removed so one concept is not double-counted.

OS2 features:
- ret1
- dist_ema20
- ema20_slope
- bars_peak_trough

OS3 features:
- ret1
- up_amp_pct
- ret4
- atr_pct
- ret8
- bars_trough_confirm
- bars_peak_trough

No new feature may enter V10.

## Partitions
- Model fit: 2023 only.
- Threshold/model selection: 2024 only.
- Frozen reference transfer: 2025 and 2026 through available data.
- V9 used 2024 for anatomy stability, so 2024 is development validation, not pristine OOS.
- 2025/2026 are not used for fit, feature choice, model choice, or threshold choice.

## Frozen model family
For each target independently:
1. LOGIT: StandardScaler + LogisticRegression(C=1.0, class_weight=balanced, max_iter=2000, random_state=314).
2. TREE: DecisionTreeClassifier(max_depth=2, min_samples_leaf=50, class_weight=balanced, random_state=314).
3. RF: RandomForestClassifier(n_estimators=300, max_depth=4, min_samples_leaf=50, max_features=sqrt, class_weight=balanced_subsample, random_state=314).

## Threshold selection
Fixed score quantiles on 2024:
50, 60, 70, 75, 80, 85, 90, 92.5, 95, 96, 97, 98, 98.5, 99 percent.

Actual execution is evaluated at every threshold with one active position.

## Frozen execution geometry
Detector evaluation uses the target-matched symmetric exit only:
- OS2 detector: TP +2% / SL -2%.
- OS3 detector: TP +3% / SL -3%.
- RR = 1:1.
- max hold = 24h.
- cost = 0.15% round trip.
- notional = USD500.
- same-5m TP+SL ambiguity = loss.

V11 may alter execution geometry only if V10 passes the detector gate.

## 2024 selection
Eligible configuration must:
- execute >=1 trade/day;
- have positive after-cost expectancy.

Rank eligible configurations by:
1. highest WR;
2. highest expectancy/trade;
3. highest mean weekly return;
4. larger N.

If none are eligible, report the >=1/day WR frontier and stop.

## V10 detector gate
A target passes V10 only if the 2024-selected frozen detector achieves ALL of:
- 2024 WR >=70%;
- 2024 >=1 trade/day;
- 2024 expectancy >0;
- 2025 WR >=70%;
- 2025 >=1 trade/day;
- 2025 expectancy >0;
- 2026 WR >=70%;
- 2026 >=1 trade/day;
- 2026 expectancy >0.

If neither OS2 nor OS3 passes, stop before V11.
If any passes, proceed to V11 execution geometry using only the passing frozen detector.