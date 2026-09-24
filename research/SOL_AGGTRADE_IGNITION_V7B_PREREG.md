# SOL High-Resolution AggTrade Ignition V7B — Preregistration

## Objective
Test whether sub-15m trade-sequence information can separate TRUE ignition from FALSE ignition inside the frozen NEW_LONG_BUILD parent state.

## Frozen parent event
- NEW_LONG_BUILD rising edge from V4/V5, unchanged.
- Signal timestamp = completed 15m bar where the parent state changes OFF -> ON.
- Entry = next 15m open.
- No new price/OI/funding threshold is introduced.

## Data source
- Binance Data Vision USD-M futures daily aggTrades for SOLUSDT.
- This is a compressed trade-sequence source with aggressor side inferred from is_buyer_maker.
- It is NOT L2, NOT an order-book replay, and NOT called full raw trade flow.
- Raw futures trades remain reserved for confirmation if V7B earns promotion.

## Development discipline
- 2023: model fit only.
- 2024: threshold/model selection and promotion gate.
- 2025/2026 remain untouched in V7B.
- No OOS files are downloaded unless V7B earns promotion.

## Execution target
- LONG only.
- TP +2.0%.
- SL -2.0%.
- RR = 1:1.
- Max hold = 24h.
- Cost = 0.15% round trip.
- USD500 notional.
- Same-5m TP+SL ambiguity = loss.
- One active position at a time during strategy evaluation.

## Causal high-resolution feature window
For every frozen parent event:
- feature end = entry timestamp;
- only aggTrades with timestamp in [entry-15m, entry) are allowed;
- subwindows: 15m, 5m, 1m, 30s;
- nothing at or after entry may enter a feature.

## Frozen feature families
For each subwindow:
1. aggressive BUY and SELL quote volume;
2. signed quote delta and delta ratio;
3. BUY/SELL trade-count imbalance;
4. first-to-last trade price return;
5. price progress per absolute signed-flow fraction;
6. top-5%-trade quote concentration;
7. maximum same-side run length;
8. side-flip rate;
9. median inter-aggTrade interval.

Cross-window features:
- final 1m delta ratio minus prior 4m delta ratio;
- final 30s delta ratio minus prior 30s delta ratio;
- final 1m trade-count burst vs prior 4m per-minute rate;
- final 1m quote-volume burst vs prior 4m per-minute rate;
- final 30s trade-count burst vs prior 30s;
- final 30s quote-volume burst vs prior 30s.

No hand-tuned magnitude threshold is allowed before model fitting.

## Forensic stability report
On 2023 and 2024 separately, report for every numeric feature:
- WIN median vs LOSS median;
- standardized mean difference WIN minus LOSS;
- orientation-free ROC AUC.

A descriptive stable differentiator requires:
- same SMD sign in 2023 and 2024;
- abs(SMD) >= 0.10 in both years.

This does not itself qualify as a trading pass.

## Frozen model family
Two model families only:
1. TREE: DecisionTreeClassifier(max_depth=2, min_samples_leaf=80, class_weight=balanced, random_state=314).
2. RF: RandomForestClassifier(n_estimators=300, max_depth=5, min_samples_leaf=80, max_features=sqrt, class_weight=balanced_subsample, random_state=314).

Both fit on 2023 only.

2024 threshold grid uses fixed score quantiles:
50%, 60%, 70%, 75%, 80%, 85%, 90%, 92.5%, 95%, 96%, 97%, 98%, 98.5%, 99%.

## 2024 selection ranking
Evaluate one-position execution for each model/threshold.
Among configurations with >=7 executed trades/week and positive expectancy:
1. highest WR;
2. highest mean weekly net return;
3. highest expectancy/trade;
4. higher trade count.

If none are positive at >=7/week, report the frontier by highest WR at >=7/week.

## Promotion gates
FULL_DEV_GATE:
- WR >=70% in 2024;
- >=7 executed trades/week;
- positive after-cost expectancy.

NEAR_DEV_GATE:
- WR >=65% in 2024;
- >=7 executed trades/week;
- positive after-cost expectancy.

Only FULL_DEV_GATE or NEAR_DEV_GATE authorizes a separately frozen raw-trade/OOS confirmation stage.

## Stop rule
If neither gate is reached, compressed trade-sequence information is insufficient for the required daily-frequency ignition target. Do not tune new quantiles, tree depths, leaf sizes, TP/SL, or parent-state thresholds inside V7B.