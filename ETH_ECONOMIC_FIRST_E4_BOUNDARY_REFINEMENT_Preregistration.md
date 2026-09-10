# ETH Economic-First E4 — Drive-Strength Boundary Refinement Preregistration

**PREREGISTERED before result-bearing execution.**

## Lineage
E3 selected the Development character:

**20:30 UTC (03:30 WIB) / REVERSAL / lookback 15m / causal strength >=0.85 / hold 720m**

with N131, net WR56.49%, net +$346.12, expectancy +$2.642/trade, PF1.695, max DD $78.67, loss streak7, 3/4 positive blocks, and 3/6 supportive neighbors.

The E3 winner touched two outer sentinels: lookback 15m was the minimum tested and strength 0.85 was the maximum tested. Hold720m was interior. E4 therefore refines **only those two boundary dimensions**.

## Frozen coordinates
- clock: **20:30 UTC**;
- response: **REVERSAL** (SHORT after positive pre-drive, LONG after negative pre-drive);
- hold: **720 minutes**;
- fixed notional: **$500**;
- round-trip cost: **$0.75**;
- weekday anchors only;
- no H/L/range/breakout/retest/EMA/Fibonacci;
- same causal rolling-strength definition as E3: at most previous 60 same-clock/lookback weekday observations, minimum 40 prior observations.

Development outcomes only are used for selection. External and Reference Validation remain closed until one interior E4 candidate is frozen.

## Refined candidate grid
### Pre-entry lookback
`5, 10, 15, 20, 30 minutes`

- 5m = lower sentinel and current raw-data resolution floor;
- 30m = upper sentinel;
- 15m is the E3 coordinate and must reproduce E3 exactly at strength0.85.

### Causal strength threshold
`0.75, 0.80, 0.825, 0.85, 0.875, 0.90, 0.925`

- 0.75 and 0.925 are outer sentinels;
- thresholds above 0.85 explicitly test the open E3 boundary;
- fractional thresholds are applied to the causal rolling percentile exactly, with no future information.

Total Development candidates: **5 × 7 = 35**.

## PnL
Linear USDT-margined fixed-notional PnL:
- LONG return = `(exit-entry)/entry`;
- SHORT return = `(entry-exit)/entry`;
- gross PnL = $500 × return;
- net PnL = gross PnL - $0.75;
- net win = net PnL > 0.

## Development high-quality gate
Because E4 intentionally tests stronger filters than E3, minimum N is reduced only enough to make the upper-strength refinement statistically executable. All other quality gates remain unchanged.

A candidate must satisfy ALL:
- >= **80** Development trades;
- net WR >= **55.0%**;
- net PnL >0;
- expectancy >= **+$0.25/trade**;
- PF >= **1.20**;
- max DD <= **$80**;
- max loss streak <= **8**;
- >= **3/4** chronological blocks with positive net PnL.

## Local stability
Neighbors vary one refined coordinate at a time:
- adjacent lookback;
- adjacent strength threshold.

A neighbor is supportive when:
- >=60 trades;
- WR >=52.0%;
- net PnL >0;
- expectancy >0;
- PF >=1.05;
- >=2/4 positive-PnL blocks.

Require at least **50% of available neighbors supportive**, with at least 2 supportive neighbors when 3 or more are available, and all available if fewer than 2 exist.

## Development selection
Among candidates passing high-quality + local-stability gates, rank lexicographically by:
1. highest expectancy / net-per-100;
2. highest net WR;
3. highest PF;
4. lowest max DD;
5. lowest max loss streak;
6. higher N;
7. shorter lookback;
8. lower strength threshold as final deterministic tie-break.

## Boundary rule
If the winner uses:
- lookback **5m or 30m**, or
- strength **0.75 or 0.925**,
status is `ETH_ECONOMIC_FIRST_E4_BOUNDARY_OPEN` and holdouts remain closed.

If the winner is interior, freeze it unchanged and open both historical holdouts.

## Historical replication
Each holdout must independently satisfy:
- >= **40** trades;
- net WR >= **53.0%**;
- net PnL >0;
- expectancy >0;
- PF >=1.10;
- max loss streak <=10.

Both must pass. Pooled results cannot rescue an individual failure. No second-best substitution after holdout failure.

## Decision
- no Development candidate: `ETH_ECONOMIC_FIRST_E4_NO_DEV_CANDIDATE`;
- sentinel winner: `ETH_ECONOMIC_FIRST_E4_BOUNDARY_OPEN`;
- interior winner + any holdout failure: `ETH_ECONOMIC_FIRST_E4_CANDIDATE_NOT_REPLICATED`;
- both holdouts pass: `ETH_ECONOMIC_FIRST_E4_SUPPORTED`.

If E4 is supported, the next step is **not** another H search. Freeze this economic character and study its causal entry/exit anatomy or economic management only.

Research/shadow only. No live promotion or profit guarantee.
