# ETH Economic-First Reset — E3 Causal Drive-Strength Preregistration

**PREREGISTERED before result-bearing execution.**

## Why E3 exists
E1 closed pure weekday clock drift. E2 closed pre-entry return **sign alone**: no candidate met the economic-health gate, although several long-horizon MOMENTUM coordinates produced positive net expectancy with poor WR / DD.

E3 asks one narrow next question:

> Does ETH become an economically clean, higher-WR momentum/reversal trade only when the **pre-entry drive is unusually strong relative to its own recent history**?

This remains economic-first. There is no H/L/reference range/breakout/retest/EMA/Fibonacci.

## Data and fixed economics
- ETHUSDT Binance Futures raw 5m;
- weekday UTC anchors only;
- External: 2020-01-01 to 2022-01-01 UTC;
- Development: 2022-01-01 to 2025-01-01 UTC;
- Reference Validation: 2025-01-01 to 2026-07-30 UTC;
- candidate selection uses Development outcomes only;
- $500 fixed notional;
- $0.75 round-trip cost;
- no compounding;
- no extra slippage model.

BTC A3.9 remains context only: WR 56.83%, expectancy +$0.6887/trade, PF 1.431, DD $31.636, max loss streak 4.

## Causal drive-strength definition
For each UTC clock and pre-entry lookback, define:

`drive(t) = open(t) / open(t-lookback) - 1`.

`abs_drive(t) = abs(drive(t))`.

The strength score at date t is calculated **only from earlier weekday observations of the same clock + lookback**:
- trailing history = at most the previous **60** valid weekday observations;
- require at least **40** previous observations before t is eligible;
- `strength_pct(t) = fraction of those prior observations with abs_drive <= current abs_drive`.

No current/future outcome participates in the score. The trailing history is allowed to cross partition boundaries because it uses price information available before t; outcome selection still reads Development only.

## Candidate family
### Entry clock
48 half-hour UTC clocks: 00:00, 00:30, ..., 23:30.

### Pre-entry lookback
`15, 30, 60, 120, 240, 360 minutes`.

### Response mode
- MOMENTUM: LONG if drive >0; SHORT if drive <0.
- REVERSAL: SHORT if drive >0; LONG if drive <0.

### Strength gate
Trade only when causal strength percentile is at least:
- **0.50** (top 50% relative strength),
- **0.67**,
- **0.75**,
- **0.80**,
- **0.85**.

0.50 and 0.85 are explicit strength sentinels.

### Fixed forward hold
`60, 120, 240, 360, 720, 960 minutes`.

60m and 960m are explicit hold sentinels. The 960m sentinel makes the E2-favored 720m region interior rather than automatically a grid edge.

Entry = exact 5m open at t. Exit = exact 5m open at t+hold.

Total Development candidate coordinates =
**48 × 6 lookbacks × 2 modes × 5 strength gates × 6 holds = 17,280**.

## PnL
Linear USDT-margined fixed-notional PnL:
- LONG return = `(exit-entry)/entry`;
- SHORT return = `(entry-exit)/entry`;
- gross PnL = $500 × gross return;
- net PnL = gross PnL - $0.75;
- net win = net PnL >0.

## Metrics
Per candidate:
- trade N, net WR, net PnL, expectancy/trade, net/100;
- PF, max DD, max win/loss streak;
- four chronological block PnLs and WRs.

## Development high-quality character gate
A candidate must satisfy ALL:
- >= **120** Development trades;
- net WR >= **55.0%**;
- net PnL >0;
- expectancy >= **+$0.25/trade**;
- PF >= **1.20**;
- max DD <= **$80**;
- max loss streak <= **8**;
- >= **3/4** chronological blocks with positive net PnL.

This is intentionally stricter on WR than E1/E2. E3 is only useful if strength conditioning exposes a materially cleaner character rather than merely another positive-expectancy low-WR tail.

## Local stability
Neighbors preserve mode and vary one coordinate at a time:
- clock ±30m;
- adjacent lookback;
- adjacent strength threshold;
- adjacent hold.

A neighbor is supportive when:
- >=100 trades;
- WR >=52.0%;
- net PnL >0;
- expectancy >0;
- PF >=1.05;
- >=2/4 positive-PnL blocks.

Require:
- >=50% of available neighbors supportive;
- at least 3 supportive neighbors when >=5 are available;
- at least 2 supportive neighbors when 3–4 are available.

## Development selection
Among candidates passing the high-quality gate + local stability, rank:
1. highest net/100 (expectancy);
2. highest net WR;
3. highest PF;
4. lowest max DD;
5. lowest loss streak;
6. higher trade N;
7. shorter hold;
8. lower strength threshold;
9. shorter lookback;
10. earlier UTC clock;
11. MOMENTUM before REVERSAL only as final deterministic tie-break.

## Boundary rule
If the selected winner touches any outer sentinel:
- lookback 15m or 360m;
- strength 0.50 or 0.85;
- hold 60m or 960m;
then status = `ETH_ECONOMIC_FIRST_E3_BOUNDARY_OPEN`; historical holdouts remain closed. No second-best substitution.

## Historical replication
If the selected winner is interior, freeze it unchanged and open External + Reference Validation independently.

Each holdout must satisfy:
- >=55 trades;
- net WR >= **53.0%**;
- net PnL >0;
- expectancy >0;
- PF >=1.10;
- max loss streak <=10.

Both must pass independently. Pooled results cannot rescue an individual failure. No second-best candidate may be tried.

## Decision
- no Development candidate → `ETH_ECONOMIC_FIRST_E3_NO_DEV_CANDIDATE` and close this family;
- sentinel winner → `ETH_ECONOMIC_FIRST_E3_BOUNDARY_OPEN`;
- holdout failure → `ETH_ECONOMIC_FIRST_E3_CANDIDATE_NOT_REPLICATED`;
- both holdouts pass → `ETH_ECONOMIC_FIRST_E3_SUPPORTED`.

If supported, only then study the winner's anatomy or TP/SL geometry. If failed, do not relax gates or return to H continuation as a rescue.

Research/shadow only. No live promotion or profit guarantee.
