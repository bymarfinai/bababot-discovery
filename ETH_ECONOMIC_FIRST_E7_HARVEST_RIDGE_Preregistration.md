# ETH Economic-First E7 — High-WR Harvest Ridge Refinement Preregistration

**PREREGISTERED before result-bearing execution.**

## Lineage and scientific purpose
E6 formally produced no candidate under its deliberately high expectancy floor of +$0.75/trade, and that gate is not relaxed.

However, the completed E6 atlas discovered a distinct positive-economic, high-WR no-SL ridge on the already-frozen E5 signal. The strongest seed balancing WR and economics was:

**TP0.60% / SL NONE / hold720m**

Development: N153 / WR78.43% / net +$64.30 / expectancy +$0.4203/trade / PF1.321 / max DD $44.43 / loss streak4 / 4/4 positive blocks.

E7 is a new bounded refinement experiment. It does not rerun the E6 family with weaker gates. Its question is:

> **Is the high-WR, positive-economic no-SL harvest ridge around TP0.60% / hold720m locally stable and historically replicable?**

## Frozen signal and entry
- ETHUSDT Binance Futures raw 5m;
- weekday anchor;
- entry clock **17:00 UTC (00:00 WIB)**;
- pre-entry lookback **360m**;
- causal strength band **B0_20 = [0.00,0.20)** using the same E3/E5 rolling percentile;
- response **MOMENTUM**;
- exact 17:00 5m open entry;
- **SL NONE** frozen;
- fixed notional **$500**;
- round-trip fee **$0.75**;
- no compounding;
- no H/L/reference range/breakout/retest/EMA/Fibonacci.

External and Reference Validation remain closed until exactly one Development candidate is frozen.

## Refined management grid
### TP
`0.50%, 0.55%, 0.60%, 0.65%, 0.70%, 0.75%, 0.80%`

- 0.50% and 0.80% are outer sentinels;
- 0.60% reproduces the E6 ridge seed.

### Maximum hold
`540, 600, 660, 720, 780, 840, 900 minutes`

- 540m and 900m are outer sentinels;
- 720m reproduces the E6 ridge seed.

Total Development candidates: **49**.

## Causal exit semantics
- only TP can terminate early;
- TP may be reached from the entry 5m bar onward;
- LONG TP = entry × (1+TP);
- SHORT TP = entry × (1-TP);
- if TP is never reached, exit at the exact 5m open at entry+hold;
- all trades pay the full $0.75 round-trip fee.

## Seed reproduction invariant
The exact E6 coordinate TP0.60% / hold720m must reproduce:
- N153;
- WR78.4313725%;
- net PnL +$64.300335 (within floating tolerance);
- expectancy +$0.420264/trade;
- PF1.321183;
- max DD $44.427636;
- loss streak4;
- 4/4 positive blocks.

Failure of this invariant invalidates the run.

## Development ridge gate
A candidate must satisfy ALL:
- >= **140 trades**;
- net WR >= **75.0%**;
- net PnL >0;
- expectancy >= **+$0.40/trade**;
- PF >= **1.20**;
- max DD <= **$60**;
- max loss streak <= **5**;
- >= **3/4** chronological blocks with positive net PnL.

These thresholds describe the newly discovered E6 ridge rather than replacing E6's formal gate.

## Local stability
Neighbors are adjacent TP and adjacent hold cells only.

A neighbor is supportive when:
- >=140 trades;
- WR >=70.0%;
- expectancy >=+$0.20/trade;
- net PnL >0;
- PF >=1.10;
- max DD <=$80;
- >=2/4 positive blocks.

Require at least **2 supportive neighbors** when 3–4 are available; otherwise at least 1 supportive neighbor.

## Development selection
Among candidates passing ridge + local-stability gates, rank lexicographically by:
1. highest expectancy / net-per-100;
2. highest WR;
3. highest PF;
4. lowest max DD;
5. lowest max loss streak;
6. shorter hold;
7. smaller TP.

The ranking prioritizes improving economics while preserving the preregistered high-WR floor.

## Boundary rule
If the Development winner uses TP0.50% or TP0.80%, or hold540m or hold900m, status is `ETH_ECONOMIC_FIRST_E7_BOUNDARY_OPEN`; holdouts remain closed and no second-best candidate is substituted.

## Historical replication
For an interior winner, freeze TP and hold unchanged and evaluate External and Reference Validation independently.

Each holdout must satisfy ALL:
- >= **50 trades**;
- net WR >= **70.0%**;
- net PnL >0;
- expectancy >0;
- PF >= **1.10**;
- max DD <= **$100**;
- max loss streak <= **7**.

Both must pass independently. Pooled results are descriptive only and cannot rescue an individual failure. No second-best substitution after failure.

## Decision
- no Development ridge candidate → `ETH_ECONOMIC_FIRST_E7_NO_DEV_CANDIDATE`;
- Development winner at sentinel → `ETH_ECONOMIC_FIRST_E7_BOUNDARY_OPEN`;
- interior winner but either holdout fails → `ETH_ECONOMIC_FIRST_E7_CANDIDATE_NOT_REPLICATED`;
- both holdouts pass → `ETH_ECONOMIC_FIRST_E7_SUPPORTED`.

If supported, freeze the ridge and compare its complete historical economics directly with BTC A3.9 before any further optimization.

Research/shadow only. No live promotion or profit guarantee.
