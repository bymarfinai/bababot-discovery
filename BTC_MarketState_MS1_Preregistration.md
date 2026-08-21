# BTC Market-State MS1 — Preregistration

**Status:** FROZEN BEFORE RESULT OBSERVATION  
**Purpose:** identify causal pre-move market states that can support high-probability LONG or SHORT decisions, using 19–20 Aug 2026 as an archetype to explain after the model is frozen — not as a threshold-tuning target.  
**Live BBC:** untouched.

## Research question
Can a low-dimensional combination of **pre-entry** BTC structure/order-flow, derivatives positioning, and lagged macro state identify LONG or SHORT opportunities with approximately **80% first-hit win rate** under executable next-hour-open entry?

The goal is not to explain a move after it happened. The goal is to test whether the information state that existed **before** a move transfers across history and survives chronological validation.

## Evidence window
- BTCUSDT USD-M perpetual 1h candles.
- Start: 2023-01-01 UTC.
- End: latest completed hour available up to 2026-08-20 UTC.
- Funding: Binance USD-M funding history, backward-asof only.
- Macro: FRED daily series, consumed with a mandatory one-day lag so the current trading day's close is never used intraday.
- Discovery = first 70% chronologically.
- Validation = final 30% chronologically.
- 19–20 Aug 2026 remains inside validation and may be described only after rules are selected from discovery.

## Entry / outcome — frozen primary test
At every eligible completed 1h bar `t`:
- features use only information available by `t` close;
- simulated entry = next 1h bar open (`t+1`);
- horizon = next 6 completed 1h bars;
- LONG TP = +1.50%, SL = -0.80%;
- SHORT TP = -1.50%, SL = +0.80%;
- if TP and SL are both touched in the same 1h bar, count SL first (adverse-first);
- if neither is hit by 6h, outcome = TIME and is not a win;
- modeled round-trip fee = 0.15% for PnL diagnostics.

Primary win-rate denominator includes all eligible state opportunities, with TIME counted non-win. This prevents flattering WR by ignoring unresolved trades.

## Frozen causal features
All rolling features are shifted/constructed using completed data only.

### BTC price / volatility
1. `ret_4h` — close return over 4h.
2. `ret_24h` — close return over 24h.
3. `compression_6_24` — 6h high-low range divided by 24h high-low range.
4. `breakout_pos_24` — close position inside prior/current completed 24h range, 0=low, 1=high.
5. `rv_24` — std of hourly returns over 24h.

### Participation / order-flow proxy
6. `rel_quote_volume_24` — current quote volume divided by trailing-24h median.
7. `taker_imbalance_3h` — aggregate `(2*taker_buy_quote - quote_volume) / quote_volume` over completed last 3h.

### Derivatives positioning
8. `funding_rate` — latest published BTCUSDT funding rate available at or before `t`.
9. `funding_z_30` — funding z-score over the latest 30 published funding observations.

No open-interest history is required in MS1 because long historical OI REST coverage is not stable enough for the full window. OI can be a future independent family only if a causal archive is first secured.

### Lagged macro
10. `dgs10_chg` — prior completed US trading day's change in 10Y Treasury yield (FRED DGS10).
11. `dollar_chg` — prior completed day's change in Broad Dollar Index (FRED DTWEXBGS).
12. `vix_chg` — prior completed day's change in VIX (FRED VIXCLS).
13. `sp500_ret` — prior completed day's S&P 500 return (FRED SP500).

Macro missing values are forward-filled only after the mandatory one-day lag; no same-day future value may leak into an intraday BTC row.

## Frozen state atoms
Thresholds are estimated **only on discovery** and then frozen for validation.

Quantile atoms use discovery 30th / 70th percentiles; breakout uses 20th / 80th percentiles.

LONG atoms:
- `COMPRESSED`: compression <= q30.
- `POS_FLOW`: taker imbalance >= q70.
- `HIGH_BREAKOUT_POS`: breakout position >= q80.
- `POS_4H`: ret_4h >= q70.
- `HIGH_VOLUME`: relative quote volume >= q70.
- `LOW_FUNDING`: funding z <= q30 OR funding rate <= 0.
- `YIELD_DOWN`: dgs10_chg <= q30.
- `DOLLAR_DOWN`: dollar_chg <= q30.
- `VIX_DOWN`: vix_chg <= q30.
- `SPX_UP`: sp500_ret >= q70.

SHORT atoms are exact directional mirrors:
- `COMPRESSED`.
- `NEG_FLOW` <= q30.
- `LOW_BREAKOUT_POS` <= q20.
- `NEG_4H` <= q30.
- `HIGH_VOLUME` >= q70.
- `HIGH_FUNDING` funding z >= q70 OR funding rate >= 0.
- `YIELD_UP` >= q70.
- `DOLLAR_UP` >= q70.
- `VIX_UP` >= q70.
- `SPX_DOWN` <= q30.

## Search space — frozen and intentionally small
For LONG and SHORT separately:
- evaluate every 2-atom and 3-atom conjunction from the corresponding frozen atom set;
- no 4+ atom combinations;
- no threshold sweep beyond the fixed quantiles above;
- no weekday/hour/session carve-out;
- no TP/SL/hold sweep;
- no post-hoc exclusion of bad periods.

## Candidate gates
A state is an **MS1 80-candidate** only if ALL hold:
1. discovery opportunities >= 30;
2. discovery WR >= 80%;
3. validation opportunities >= 12;
4. validation WR >= 75%;
5. pooled WR >= 80%;
6. discovery and validation modeled net expectancy per opportunity > 0;
7. validation must contain opportunities in at least 3 chronological quartiles;
8. no data-integrity / causality violation.

A stricter **MS1 validated-80 state** additionally requires validation WR >= 80%.

If no state passes, verdict is `NO_80_STATE_FOUND_MS1`. That is a valid and preferred conclusion over threshold rescue.

## 19–20 Aug archetype audit
After candidate selection is frozen from discovery:
- identify the strongest forward +6h BTC move beginning during 19–20 Aug 2026;
- print the pre-entry feature snapshot;
- report which frozen LONG/SHORT atoms were active;
- report whether any preselected discovery candidate would have fired.

This audit is explanatory only. It cannot create or modify a rule.

## Anti-overfit lock
After observing MS1 results, do **not** rescue failure by:
- changing 30/70 or 20/80 thresholds;
- adding arbitrary EMA/Fibonacci/order-block filters;
- selecting a specific hour/day because it worked;
- changing TP/SL/horizon;
- using 19–20 Aug to define a threshold;
- isolating one macro series or one side post-hoc;
- adding OI/liquidation history without a separately preregistered data-feasibility and causal protocol.

Any follow-up must be MS2+ with a materially new information source or a genuinely independent validation question.
