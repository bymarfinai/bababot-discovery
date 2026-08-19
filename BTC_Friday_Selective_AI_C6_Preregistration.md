# BTC Friday C6 — Selective Walk-Forward AI Candle Identifier

**FROZEN BEFORE RESULT. Research-only; live BBC untouched.**

## Objective
Test the strongest still-distinct hypothesis for the user's "AI robot finds the right candle" idea: at each Friday, train only on prior Fridays, score every completed BTC 15m candle that Friday, and take at most one highest-confidence next-open trade only when predicted executable win probability is at least 80%.

This is not a same-sample tree. Every scored Friday is pseudo-OOS relative to its model.

## Frozen source rows
Inner-join the already-produced causal rows from:
- `BTC_Friday_15m_Candle_Taker_C4_Rows.csv`
- `BTC_Friday_15m_Derivatives_C5_Rows.csv`
by exact `signal_ts`.

Thus execution labels remain the already-frozen next-15m-open TP1.30% / SL1.30% / max6h / 0.15% cost outcomes. No outcomes are recomputed or changed.

## Frozen feature set
Use these causal features only:
### Candle/price
- signal_ret
- body_ratio
- upper_ratio
- lower_ratio
- close_pos
- range_open
- prior1h_ret
### Candle participation
- taker_imbalance
- taker_delta_vs_prior3
- rel_quote_volume_24h
- rel_range_prior12
### Derivatives state
- top_vs_global
- top_pos_chg15
- global_chg15
- taker_log
- oi_chg15
- oi_chg60

No local hour, weekday sub-filter, support/resistance, EMA, funding, liquidation, symbol metadata, or post-entry variables.

## LONG/SHORT labels
C4/C5 contain CONTINUATION and REVERSAL outcomes. Convert deterministically:
- green signal: LONG=CONT, SHORT=REV
- red signal: LONG=REV, SHORT=CONT

PnL is mapped identically.

## Walk-forward protocol
- order by unique Friday-WIB date
- first **52 Friday dates** are warmup only
- for every later Friday `D`, fit using all rows from Friday dates strictly earlier than `D`
- no current-Friday row enters fit, imputation, or model selection
- discovery-only/training-only median imputation each fold
- fit exactly two binary models: `P(LONG win)` and `P(SHORT win)`

Model for both sides:
`HistGradientBoostingClassifier(loss='log_loss', learning_rate=0.05, max_iter=100, max_depth=3, min_samples_leaf=30, l2_regularization=1.0, random_state=20260819)`

No model/hyperparameter sweep.

## Frozen selection policy
For each candidate candle in Friday D:
- compute `p_long` and `p_short`
- candidate direction = side with larger probability
- candidate confidence = max(p_long,p_short)

Across that Friday select exactly the single candidate with highest confidence; tie-break by earliest signal timestamp.

TRADE only if confidence >= **0.80**. Otherwise WAIT for the whole Friday.

Thus maximum one C6 trade per Friday. There is no overlapping-position issue.

## Controls / diagnostics
Report:
- number of OOS Fridays scored
- trade coverage
- observed WR, PnL, expectancy, PF
- probability calibration buckets (<0.5, 0.5–0.6, 0.6–0.7, 0.7–0.8, >=0.8) for each Friday's top candidate
- four chronological OOS blocks
- selected LONG vs SHORT attribution

No threshold sweep is allowed from calibration output.

## Frozen promotion gate
`BTC_FRIDAY_C6_SELECTIVE_AI_80_CANDIDATE` only if ALL hold:
1. pseudo-OOS selected trades N >= 30;
2. observed pseudo-OOS WR >= 80%;
3. total pseudo-OOS PnL > 0;
4. expectancy/trade > 0;
5. PF > 1.30;
6. at least 3/4 chronological OOS blocks have >=5 trades, positive PnL, and WR >=65%;
7. no training/current-Friday leakage or row-integrity violation.

Otherwise `REJECT_C6_SELECTIVE_AI_IDENTIFIER`.

## Guardrail
No confidence threshold change, second-best-candle rescue, top-N portfolio, model change, feature deletion/addition, calibration trick, or side-specific threshold after seeing C6. If C6 fails, we do not claim a robust causal BTC-Friday 80% candle identifier from the historical information sets tested so far.