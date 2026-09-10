# ETH Economic-First Reset — E1 Clock Drift Preregistration

**PREREGISTERED before result-bearing execution.**

## Why this reset exists
The prior ETH G1–G4 lineage was selected primarily through H/range continuation structure. G5 then found **0/630 static TP×SL×hold configurations with positive net Development PnL** under fixed costs. G6 showed favorable excursion exists, but that does not change the fact that the upstream family was not discovered using the real objective.

E1 therefore changes the discovery objective, not the thresholds of G5:

> **Find a pair-native ETH character that already looks economically healthy under a deliberately crude executable trade rule, before spending experiments on anatomy.**

No H, L, reference range, breakout, retest, Fibonacci, EMA, or prior ETH/SOL/BTC coordinate is used in E1.

## Data
ETHUSDT Binance Futures raw 5m using the existing repository loader.

Frozen partitions:
- External: 2020-01-01 to 2022-01-01 UTC;
- Development: 2022-01-01 to 2025-01-01 UTC;
- Reference Validation: 2025-01-01 to 2026-07-30 UTC.

Only **weekday anchors (Monday–Friday)** are eligible in E1. This is one bounded family; weekend character is a separate future family if needed.

Candidate selection reads **Development only**. External and Reference Validation remain closed until exactly one interior Development candidate is frozen.

## Economics
- fixed notional = **$500** per trade;
- round-trip cost = **$0.75** per trade;
- no compounding;
- no extra slippage model;
- net win = net PnL > 0 after the $0.75 cost.

BTC A3.9 remains descriptive benchmark only:
- 139 trades;
- WR 56.83%;
- net +$95.734;
- expectancy +$0.6887/trade;
- PF 1.431;
- max DD $31.636;
- max loss streak 4.

## Candidate family — no H
For every weekday UTC date anchor:

### Entry clock
Every 30 minutes across 24h:
`00:00, 00:30, ..., 23:30 UTC` = **48 clocks**.

Entry is the exact 5m **open** at that clock.

### Direction
- LONG
- SHORT

### Fixed holding horizon
`15, 30, 60, 90, 120, 180, 240, 360, 480, 720, 960 minutes`.

Exit is the exact 5m **open** at `entry clock + hold`.

15m and 960m are explicit outer hold sentinels. Clock is circular and has no edge. No stop or target is used: the purpose is to expose raw time-of-day directional economic character with minimum management assumptions.

Total Development candidates:
**48 clocks × 2 directions × 11 holds = 1,056**.

A trade is included only when both exact entry and exact exit bars exist and the complete interval lies inside the requested partition.

## Trade PnL
This is linear USDT-margined fixed-notional PnL.

LONG gross return = `(exit - entry) / entry`.

SHORT gross return = `(entry - exit) / entry`.

Gross PnL = `$500 × gross return`.

Net PnL = `gross PnL - $0.75`.

## Metrics
For every candidate report:
- trades;
- net wins / losses;
- net WR;
- gross PnL;
- total fees;
- net PnL;
- expectancy/trade;
- net PnL per 100 trades;
- PF from net trade PnLs;
- max cumulative-PnL drawdown;
- max net-loss streak;
- max net-win streak;
- four chronological block PnLs and block WRs.

## Development healthy-character gate
A candidate must satisfy all:
- >= **700** Development trades;
- net WR >= **52.0%**;
- net PnL > 0;
- expectancy >= **+$0.10/trade**;
- PF >= **1.10**;
- max DD <= **$100**;
- max loss streak <= **10**;
- >= **3/4** chronological blocks with positive net PnL.

This gate is intentionally economic. No continuation proxy can rescue a candidate.

## Local economic stability
For each candidate, neighbors are the same direction at:
- clock -30m, same hold;
- clock +30m, same hold;
- immediately shorter preregistered hold, when available;
- immediately longer preregistered hold, when available.

A neighbor is supportive when:
- >=700 trades;
- net PnL > 0;
- expectancy > 0;
- PF >=1.00;
- net WR >=50.5%;
- >=2/4 positive-PnL blocks.

An eligible candidate needs at least **2 supportive neighbors** (or all available if fewer than 2 exist).

## Development selection
Among candidates passing both healthy-character and local-stability gates, rank lexicographically by:
1. highest net PnL per 100 trades / expectancy;
2. highest net WR;
3. highest PF;
4. lowest max DD;
5. lowest max loss streak;
6. shortest hold;
7. earliest UTC clock;
8. LONG before SHORT only as final deterministic tie-break.

This explicitly makes actual economics the primary objective while retaining WR as the next co-primary quality measure.

## Boundary rule
If the Development winner uses hold **15m or 960m**, status is `ETH_ECONOMIC_FIRST_E1_HOLD_BOUNDARY_OPEN`; holdouts remain closed. No second-best substitution.

## Historical replication
If the winner is interior, freeze clock, direction, and hold unchanged and evaluate independently on External and Reference Validation.

Each holdout must satisfy:
- >=300 trades;
- net WR >= **50.5%**;
- net PnL > 0;
- expectancy > 0;
- PF >= **1.05**;
- max loss streak <= **15**.

Both holdouts must pass independently. Pooled results are descriptive only and cannot rescue an individual failure. No second-best candidate is tried after a holdout failure.

## Decision
- no eligible Development candidate → `ETH_ECONOMIC_FIRST_E1_NO_DEV_CANDIDATE` and close this clock-drift family;
- sentinel winner → `ETH_ECONOMIC_FIRST_E1_HOLD_BOUNDARY_OPEN`;
- interior winner but either holdout fails → `ETH_ECONOMIC_FIRST_E1_CANDIDATE_NOT_REPLICATED`;
- both holdouts pass → `ETH_ECONOMIC_FIRST_E1_SUPPORTED`.

If E1 fails, do **not** return to H tuning. Close pure clock drift and test a different economic-first character family. If E1 succeeds, only then study its anatomy to understand and improve WR/economics.

Research/shadow only. No live promotion or profit guarantee.
