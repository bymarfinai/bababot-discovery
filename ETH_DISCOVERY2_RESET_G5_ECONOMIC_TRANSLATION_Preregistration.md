# ETH Discovery 2 Reset — G5 Economic Translation Preregistration

**PREREGISTERED before result-bearing execution.**

## Frozen parent
G5 inherits the historically supported G2+G3+G4 lineage unchanged:
- ETHUSDT Binance Futures raw 5m;
- LONG;
- reference start **01:30 UTC (08:30 WIB)**;
- reference duration **R180**;
- execution horizon **E720**;
- first valid HIGH-side pressure;
- DIRECT B00 = first strict completed close above H after pressure;
- executable entry = **NEXT_OPEN**, the open of the next 5m bar after completed B00.

No clock, range, structure, or entry coordinate may be changed in G5.

## Scientific question
> On the frozen ETH-native lineage, which finite TP × SL × maximum-hold geometry produces positive, stable economics on Development and then replicates unchanged on both historical holdouts?

G5 is the first reset-lineage money experiment. It does not add filters or regime conditions.

## Data partitions
Reuse the frozen partitions:
- External: 2020-01-01 to 2022-01-01;
- Development: 2022-01-01 to 2025-01-01;
- Reference Validation: 2025-01-01 to 2026-07-30.

Candidate selection reads Development only. External and Reference Validation remain closed until one Development candidate is frozen.

## Fixed economics
- Fixed notional: **$500 per trade**.
- Equivalent research sizing context: $10 margin × 50x = $500 notional; no compounding.
- Round-trip trading cost: **0.15% of notional = $0.75/trade**.
- No additional slippage model in G5.
- Net PnL = `$500 × (exit_price / entry_price - 1) - $0.75`.
- Net win = net PnL > 0 after fee.

The BTC comparison uses the same fixed-$500 / $0.75-cost basis.

## Frozen candidate grid
TP distance is measured upward from NEXT_OPEN entry in units of the frozen session range R.
SL distance is measured downward from NEXT_OPEN entry in units of R.

TP grid:
- **0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.30, 0.40, 0.60, 0.80 R**.

SL grid:
- **0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.30, 0.40, 0.60 R**.

Maximum holding-time grid:
- **15, 30, 60, 120, 240, 480, 720 minutes**.

Total Development configurations = **10 × 9 × 7 = 630**.

Historical Z6 `TP0.60R / SL0.30R / 120m` is included only because its coordinates naturally lie inside this preregistered grid. It has no inherited preference or status.

## Causal trade simulation
Entry occurs at the frozen NEXT_OPEN price.

For each 5m bar from the entry bar forward until the earlier of max-hold or frozen execution end:
- TP hit if bar high >= entry + TP×R;
- SL hit if bar low <= entry - SL×R;
- if TP and SL are both reachable inside the same 5m bar, intrabar ordering is unknown and G5 conservatively records **SL**;
- otherwise first uniquely observed TP/SL terminates the trade.

If neither level is reached, exit at the close of the last complete 5m bar ending no later than the max-hold/execution deadline. No bar after the frozen execution end may contribute.

## Metrics
For every configuration report:
- trades;
- TP / SL / timeout counts;
- net win rate;
- gross PnL, fees, net PnL;
- expectancy per trade;
- net PnL per 100 trades;
- profit factor;
- max dollar drawdown from chronological cumulative net PnL;
- max loss streak / max win streak;
- average and median hold minutes;
- four chronological Development block PnLs and number of positive blocks.

## Development gate
A configuration must satisfy ALL:
- >=150 trades;
- net PnL > 0;
- expectancy > 0;
- PF >= **1.20**;
- max DD <= **$40**;
- max loss streak <= **8**;
- >=3 of 4 chronological block PnLs positive.

## Local economic stability
For each configuration, orthogonal one-step neighbors are the immediately adjacent preregistered TP, SL, and hold coordinates when available.

A neighbor is supportive if:
- net PnL > 0;
- PF >= 1.10;
- max DD <= $50;
- >=3/4 positive Development blocks.

A candidate must have at least `max(2, ceil(50% of available neighbors))` supportive neighbors. This prevents promotion of an isolated money-grid spike.

## Development-only selection
Among Development candidates passing the gate + local stability, rank lexicographically by:
1. highest net PnL per 100 trades;
2. highest PF;
3. lowest max DD;
4. highest net WR;
5. lowest max loss streak;
6. shorter max hold;
7. smaller SL;
8. smaller TP.

No holdout metric participates in selection.

## Boundary rule
Outer sentinels are:
- TP = 0.05R or 0.80R;
- SL = 0.05R or 0.60R;
- hold = 15m or 720m.

If the selected Development winner lies on ANY outer sentinel, status = `ETH_DISCOVERY2_RESET_G5_BOUNDARY_OPEN`; historical holdouts remain closed. No second-best substitution is allowed.

## Historical replication
For an interior frozen winner, each holdout must independently satisfy:
- >=70 trades;
- net PnL > 0;
- expectancy > 0;
- PF >= **1.10**;
- max DD <= **$45**;
- max loss streak <= **8**.

Pooled holdout must additionally satisfy:
- net PnL > 0;
- PF >= **1.15**.

Both independent holdouts and pooled holdout must pass unchanged.

## BTC benchmark context
After historical replication, report the selected ETH configuration across all three historical partitions and compare it with the frozen BTC A3.9 preferred-consistency benchmark:
- trades: **139**;
- WR: **56.83%**;
- net PnL: **+$95.734**;
- expectancy: **+$0.6887/trade**;
- net per 100 trades: **+$68.873**;
- PF: **1.431**;
- max DD: **$31.636**;
- max loss streak: **4**.

BTC comparison is descriptive and cannot rescue or invalidate the preregistered ETH replication result. Because trade counts differ, expectancy, net/100, PF, DD, and streak are more decision-useful than raw total net alone.

## Decision rules
- no Development candidate -> `ETH_DISCOVERY2_RESET_G5_NO_DEV_CANDIDATE`;
- selected candidate on any sentinel -> `ETH_DISCOVERY2_RESET_G5_BOUNDARY_OPEN`;
- interior candidate fails either independent holdout or pooled holdout -> `ETH_DISCOVERY2_RESET_G5_CANDIDATE_NOT_REPLICATED`;
- all replication gates pass -> `ETH_DISCOVERY2_RESET_G5_SUPPORTED`.

No post-hoc threshold relaxation, second-best substitution, filter rescue, or coordinate tweak is permitted inside G5.

Research/shadow only. No live promotion or profit guarantee.
