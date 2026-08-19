# BTC Global/Pooled Regime Engine — G4 Preregistration

**Status: PREREGISTERED BEFORE G4 EXECUTION — research only; live BBC untouched.**

## Why G4 exists
G0/G1 proved that a generic 50bp first-passage market regime is causally predictable from pooled hourly BTC states. G1/G2/G3 also showed a separate fact: that generic directional regime is not sufficiently aligned with the frozen Tuesday A5.11 economics. Many Tuesday trades remain profitable even when the generic pooled regime is globally BUY-like or when relative SELL lift is below 1.

Therefore G4 does **not** tune the G1 gate. It changes the pooled training target to the execution question we actually care about, while keeping the sample universe large and the downstream Tuesday strategy frozen.

## Core hypothesis
Instead of training only on ~139 Tuesday outcomes, create a hypothetical frozen A5.11 SELL outcome at **every eligible hourly BTC state**.

Question at each state `t`:

> If the already-frozen Tuesday A5.11 SELL stack were opened at this hourly state, would its net PnL be positive?

This produces tens of thousands of execution-aligned labels from all days/hours without changing the Tuesday rules.

## Frozen execution label — no retuning
For every eligible hourly decision timestamp use exactly the existing frozen Tuesday A5.11 stack:

- SELL at decision bar open.
- TP = 1.35%.
- SL = 0.80%.
- Max hold = 6h.
- Same $500 reference notional and 0.15% round-trip fee convention.
- A5.2 unchanged.
- A5.9 FastMR unchanged.
- A5.11 EMA7 runner recovery unchanged.
- Existing parent intrabar ordering/parity conventions unchanged.

Primary binary target:
- `WIN = 1` iff frozen A5.11 net PnL > 0.
- `WIN = 0` otherwise.

No TP/SL/management sweep is allowed.

## Mandatory parity anchor
Before any pooled G4 result is accepted, the generic hourly simulator must reproduce the existing 139 historical Tuesday A5.11 anchor:

- 139 trades,
- 89 wins,
- approximately +$130.33 PnL,
- A5.2 / A5.9 / A5.11 action counts matching the frozen parity checks.

If parity fails, G4 stops. The simulator is fixed; the strategy is not retuned.

## Frozen feature set
Use exactly the 17 market-only pre-entry G0 features:
- ret1h / 3h / 6h / 12h / 24h,
- ema_spread,
- dist_ema20,
- ema20_slope1h,
- loc24,
- range6 / range24 / range6_to_24,
- taker1h / taker4h,
- rv1h / rv6h,
- atr20_pct.

No calendar/day/hour features. No feature selection.

## Primary G4 model — locked
- median imputation fit on training only,
- standardization fit on training only,
- L2 logistic regression,
- `C=1.0`,
- `solver=lbfgs`,
- no class weighting,
- no feature selection,
- no hyperparameter sweep.

Primary decision rule:
- `p(WIN) >= 0.50` => TRADE
- `p(WIN) < 0.50` => WAIT

The 0.50 rule is fixed before execution; no sensitivity thresholds are candidate selectors in G4.

## Embargoed monthly walk-forward — locked
Same causal schedule as G1:
- first scored month: March 2024,
- one model frozen per calendar month,
- training rows only where `decision_t + 6h <= month_start`,
- predict the whole month with that frozen model,
- historical scoring ends at the Jul-30 cutoff.

The 6h outcome embargo applies because G4 labels use the complete frozen 6h execution horizon.

## Causal no-skill baseline
For each prediction month, baseline `p(WIN)` is the WIN rate in that month’s training set only.

Report:
- model log loss vs causal prior baseline,
- Brier vs causal prior baseline,
- ROC AUC,
- accuracy,
- predicted TRADE coverage,
- actual WR among predicted TRADE states,
- unconditional pseudo-OOS WIN rate,
- four chronological pooled blocks.

## G4 pooled-model acceptance gate — locked
All must pass:

1. At least **18,000** pseudo-OOS hourly predictions.
2. All monthly 6h embargo checks pass.
3. Model log loss < causal prior baseline log loss.
4. Model Brier < causal prior baseline Brier.
5. ROC AUC >= **0.55**.
6. Predicted TRADE coverage >= **20%**.
7. Actual WIN rate among predicted TRADE states is at least **3 percentage points above** unconditional pseudo-OOS WIN rate.
8. Model log loss beats prior baseline in at least **3 of 4** chronological pooled blocks.

No gate is changed after results.

## Frozen Tuesday overlay — locked
Map the causal G4 predictions onto the exact eligible Tuesday 06:00 WIB opportunities.

- TRADE iff `p(WIN) >= 0.50`.
- WAIT otherwise.
- A5.11 realized PnL remains frozen.

Compare against always-trade A5.11 on the exact same Tuesday subset.

### Tuesday shadow-promotion gate
All must pass:
1. Coverage >= **35%**.
2. Expectancy per opportunity > always-trade.
3. Total PnL >= always-trade.
4. Trade WR > always-trade.
5. Positive PnL delta in at least **3 of 4** chronological Tuesday blocks.

Passing means SHADOW CANDIDATE only, never automatic live promotion.

## August 2026 — report only
After all historical scoring is complete:
- fit one final G4 model using only pooled labels through Jul-30,
- freeze it across Aug 4/11/18,
- score the three Tuesday states,
- no August outcome refit,
- report p(WIN), TRADE/WAIT, and frozen A5.11 PnL.

August is diagnostic only because it has already been extensively observed.

## Explicitly prohibited
- TP/SL/hold/A5.x tuning,
- feature selection,
- XGBoost / RF / neural nets,
- threshold sweeps,
- calendar features,
- fitting only Tuesday outcomes,
- August-driven changes,
- touching live BBC.

If G4 fails, the execution-aligned pooled hypothesis fails under this predeclared simple model. Any later model-family or feature-family experiment must be separately preregistered.
