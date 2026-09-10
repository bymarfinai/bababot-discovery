# ETH Economic-First Reset — E2 Drive Response Preregistration

**PREREGISTERED before result-bearing execution.**

## Question
E1 closed pure clock drift. E2 adds exactly one causal conditioning variable:

> Given the sign of ETH's pre-entry return at a specific UTC clock, is the pair economically characterized by **momentum** or **reversal** over a subsequent fixed horizon?

Selection is based on actual fee-adjusted trading economics and WR, not H/L continuation.

## Data and fixed economics
- ETHUSDT Binance Futures raw 5m;
- weekday UTC anchors only;
- External 2020-01-01–2022-01-01;
- Development 2022-01-01–2025-01-01;
- Reference Validation 2025-01-01–2026-07-30;
- Development only for selection;
- $500 fixed notional;
- $0.75 round-trip cost;
- no compounding; no extra slippage model.

No H, L, reference range, breakout, retest, EMA, Fibonacci, or old pair coordinate is used.

## Candidate family
### Clock
48 entry clocks every 30 minutes UTC.

### Pre-entry lookback
`15, 30, 60, 120, 240, 360 minutes`.

At clock `t`, compute exact-open return:
`drive = open(t) / open(t-lookback) - 1`.

If drive = 0 exactly, skip that date.

### Response mode
- **MOMENTUM**: LONG when drive > 0, SHORT when drive < 0.
- **REVERSAL**: SHORT when drive > 0, LONG when drive < 0.

### Forward hold
`15, 30, 60, 120, 240, 360, 720 minutes`.

Entry = exact 5m open at `t`.
Exit = exact 5m open at `t + hold`.

Lookback 15/360 and hold 15/720 are explicit outer sentinels.

Total Development candidates = **48 × 6 × 2 × 7 = 4,032**.

A trade is included only when the lookback start, entry, and exit lie inside the same partition and exact 5m bars exist with the expected spacing.

## PnL
Linear USDT-margined fixed-notional PnL:
- LONG return = `(exit-entry)/entry`;
- SHORT return = `(entry-exit)/entry`;
- gross PnL = $500 × return;
- net PnL = gross PnL - $0.75;
- net win = net PnL > 0.

## Metrics
Per candidate:
- trades, net WR, net PnL, expectancy, net/100;
- PF, max DD, max loss/win streak;
- 4 chronological block PnLs and WRs.

## Development healthy-character gate
ALL required:
- >=700 trades;
- net WR >=52.0%;
- net PnL >0;
- expectancy >=+$0.10/trade;
- PF >=1.10;
- max DD <=$100;
- max loss streak <=10;
- >=3/4 positive-PnL chronological blocks.

## Local stability
Neighbors preserve response mode and vary one coordinate at a time:
- clock ±30m;
- immediately adjacent lookback values;
- immediately adjacent hold values.

A neighbor is supportive when:
- >=700 trades;
- WR >=50.5%;
- net PnL >0;
- expectancy >0;
- PF >=1.00;
- >=2/4 positive-PnL blocks.

Require at least **60% supportive available neighbors**, and at least **3 supportive neighbors when 5+ are available**; at least 2 when 3–4 are available.

## Development selection
Among full-gate candidates, rank:
1. highest net/100 (equivalent to expectancy);
2. highest net WR;
3. highest PF;
4. lowest max DD;
5. lowest loss streak;
6. shorter hold;
7. shorter lookback;
8. earlier UTC clock;
9. MOMENTUM before REVERSAL only as final deterministic tie-break.

## Boundary rule
If selected lookback is 15 or 360m, or hold is 15 or 720m, status = `ETH_ECONOMIC_FIRST_E2_BOUNDARY_OPEN`; holdouts remain closed. No second-best substitution.

## Holdout gate
Freeze one interior Development winner. External and Reference Validation must each independently satisfy:
- >=300 trades;
- net WR >=50.5%;
- net PnL >0;
- expectancy >0;
- PF >=1.05;
- max loss streak <=15.

Both must pass. Pooled holdout cannot rescue either failure. No second-best candidate is attempted after replication failure.

## Decisions
- no Development candidate → `ETH_ECONOMIC_FIRST_E2_NO_DEV_CANDIDATE` and close drive-response family;
- boundary winner → `ETH_ECONOMIC_FIRST_E2_BOUNDARY_OPEN`;
- holdout failure → `ETH_ECONOMIC_FIRST_E2_CANDIDATE_NOT_REPLICATED`;
- both holdouts pass → `ETH_ECONOMIC_FIRST_E2_SUPPORTED`.

If supported, anatomy may be studied afterward to improve an already economically healthy character. If not supported, move to another economic-first family rather than H optimization.

Research/shadow only. No live promotion or profit guarantee.
