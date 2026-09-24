# SOL Derivatives-State Transition V4 — Preregistration

## Why this exists
V3 showed that raw/regime-mixed derivatives features carry some development-period information, but do not transfer. Feature importance was dominated by OI change, top-trader-vs-global positioning, top-account positioning, and funding regime rather than instantaneous 15m taker flow.

V4 is a finite, interpretable test of regime-normalized derivatives STATE TRANSITIONS. It is not a threshold search.

## Frozen execution
- SOLUSDT USD-M perpetual.
- Signal known after completed 15m bar.
- Entry = next 15m open.
- one active position
- cost 0.15% RT, USD500 notional
- TP/SL:
  - L2 +2% / -1%, max hold 24h
  - L3 +3% / -1%, max hold 48h
  - L5 +5% / -1%, max hold 72h
- same-5m TP+SL ambiguity = loss
- all derivatives/funding observations strictly before entry

## Regime normalization
On the merged 15m timeline, using only past/current causal values:
- OI 60m change z-score over trailing 7 days (min 2 days)
- OI 4h change z-score over trailing 7 days
- top-vs-global positioning z-score over trailing 7 days
- top-account level z-score over trailing 7 days
- 60m taker imbalance z-score over trailing 7 days
- quote-volume burst z-score over trailing 7 days
- funding z30 from completed funding observations
- 1h price return and 15m return are current completed price information

No optimized magnitude threshold is allowed. Every state uses only sign tests (>0 or <0) and explicitly frozen logical combinations.

## Frozen state family
1. NEW_LONG_BUILD
   - 1h price return > 0
   - 60m taker imbalance > 0
   - OI 60m z > 0

2. FRESH_LONG_BUILD
   - NEW_LONG_BUILD
   - top-vs-global z < 0
   Interpretation: new longs enter while top traders are not already more long-skewed than their recent regime.

3. SHORT_SQUEEZE
   - 1h price return > 0
   - 60m taker imbalance > 0
   - OI 60m z < 0
   - top-vs-global z < 0

4. LOW_FUNDING_SQUEEZE
   - SHORT_SQUEEZE
   - funding_z30 < 0

5. ABSORPTION_RELEASE
   - prior 1h return <= 0
   - current 15m return > 0
   - 60m taker imbalance > 0
   - OI 60m z >= 0

6. DELEVERAGING_REVERSAL
   - 1h price return > 0
   - OI 60m z < 0
   - funding_z30 < 0

## Evaluation
No model fitting and no threshold selection.

For every state × L2/L3/L5, report separately:
- 2023
- 2024
- 2025
- 2026 through available data

Metrics:
- executed trades
- trades/week
- WR
- after-cost expectancy/trade
- mean/median weekly net return
- positive-week rate
- weeks >= +5%, >= +10%
- hit rate and early-hit rate on corresponding ex-post long legs

## Gate
A state is considered structurally promising only if:
- expectancy >0 in at least 3 of 4 calendar partitions INCLUDING 2025 and 2026,
- combined 2025+2026 expectancy >0,
- at least 2 trades/week in 2024 and 2025,
- no individual 2025/2026 WR collapse that makes expectancy negative.

No rescue thresholds are permitted inside V4.
