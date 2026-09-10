# ETH Economic-First E6 — Low-Drive MOMENTUM Management Preregistration

**PREREGISTERED before result-bearing execution.**

## Lineage
E5 isolated the strongest economic substrate inside the E2 anchor:

**17:00 UTC / lookback360m / causal strength B0_20 [0.00,0.20) / MOMENTUM**

Development with the inherited 720m time exit:
- N153
- WR49.02%
- net +$291.10
- expectancy +$1.90/trade
- PF1.631
- max DD $119.84
- max loss streak5
- 3/4 positive blocks

This is not yet a promoted strategy because WR remains below the E5 gate. E6 asks whether a simple causal management rule can convert the already-positive payoff distribution into materially higher WR **without destroying economics**.

## Frozen signal and entry
- ETHUSDT Binance Futures raw 5m;
- weekday anchors only;
- clock **17:00 UTC (00:00 WIB)**;
- pre-entry drive lookback **360m**;
- causal rolling strength exactly as E3/E5;
- trade only B0_20: `0.00 <= strength_pct < 0.20`;
- response **MOMENTUM**: LONG after positive 360m drive, SHORT after negative 360m drive;
- entry at exact **17:00 5m open**;
- fixed notional **$500**;
- fixed round-trip cost **$0.75**;
- no compounding;
- no H/L/reference range/breakout/retest/EMA/Fibonacci.

## Management family
### Take-profit distance from entry
`0.20%, 0.30%, 0.40%, 0.60%, 0.80%, 1.00%, 1.50%, 2.00%`

0.20% and 2.00% are TP outer sentinels.

### Stop-loss
- `NONE` (time exit only if TP is not reached), or
- `0.50%, 0.75%, 1.00%, 1.50%, 2.00%, 3.00%`

0.50% and 3.00% are numeric-SL outer sentinels. `NONE` is a distinct management type, not a boundary coordinate.

### Maximum holding time
`120, 240, 360, 480, 720, 960 minutes`

120m and 960m are hold outer sentinels.

Total candidates: **8 TP × 7 SL modes × 6 holds = 336**.

## Causal execution semantics
- Entry occurs at the exact 17:00 bar open.
- TP/SL can be reached from that entry bar onward.
- LONG: TP=entry×(1+tp), SL=entry×(1-sl).
- SHORT: TP=entry×(1-tp), SL=entry×(1+sl).
- For numeric SL, the first 5m bar reaching TP or SL determines the exit.
- If both TP and SL are reachable in the same first-hit 5m bar, intrabar ordering is unknowable and the trade is conservatively assigned **SL first**.
- For `SL_NONE`, only TP can terminate early.
- If no early exit occurs, exit at the exact 5m open at entry+hold.
- Every trade pays the full $0.75 round-trip cost.

## Development quality gate
A candidate must satisfy ALL:
- >=120 trades;
- net WR >= **55.0%**;
- net PnL >0;
- expectancy >= **+$0.75/trade**;
- PF >= **1.20**;
- max DD <= **$100**;
- max loss streak <= **8**;
- >=3/4 chronological blocks with positive net PnL.

The expectancy floor is deliberately above BTC A3.9's +$0.6887/trade. The aim is not to manufacture WR by accepting weak economics.

## Local management stability
Neighbors preserve signal and vary one management coordinate at a time:
- adjacent TP;
- adjacent hold;
- for numeric SL, adjacent numeric SL.

`SL_NONE` does not count as adjacent to a numeric SL.

A neighbor is supportive when:
- >=120 trades;
- WR >=52.0%;
- net PnL >0;
- expectancy >0;
- PF >=1.05;
- >=2/4 positive-PnL blocks.

Require at least **2 supportive neighbors** when at least 3 are available, otherwise at least 1 supportive neighbor.

## Development ranking
Among candidates passing the quality + local-stability gates, rank:
1. highest net WR;
2. highest expectancy / net-per-100;
3. highest PF;
4. lowest max DD;
5. lowest max loss streak;
6. shorter hold;
7. smaller TP;
8. `SL_NONE` before numeric SL only as final deterministic tie-break.

## Boundary rule
If the Development winner uses an outer TP sentinel, outer hold sentinel, or outer numeric-SL sentinel, status is `ETH_ECONOMIC_FIRST_E6_BOUNDARY_OPEN` and holdouts remain closed.

An `SL_NONE` winner may proceed to holdouts if TP and hold are interior.

## Historical replication
For an interior winner, freeze TP/SL/hold unchanged and evaluate External and Reference Validation independently.

Each holdout must satisfy:
- >=50 trades;
- net WR >= **52.0%**;
- net PnL >0;
- expectancy >0;
- PF >=1.05;
- max loss streak <=10.

Both must pass independently. No second-best substitution after holdout failure.

## Decision
- no Development candidate: `ETH_ECONOMIC_FIRST_E6_NO_DEV_CANDIDATE`;
- boundary winner: `ETH_ECONOMIC_FIRST_E6_BOUNDARY_OPEN`;
- interior winner + holdout failure: `ETH_ECONOMIC_FIRST_E6_CANDIDATE_NOT_REPLICATED`;
- both holdouts pass: `ETH_ECONOMIC_FIRST_E6_SUPPORTED`.

Research/shadow only. No live promotion or profit guarantee.
