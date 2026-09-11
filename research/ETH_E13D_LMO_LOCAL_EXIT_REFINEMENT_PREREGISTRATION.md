# ETH E13D — LMO Local Exit Refinement Preregistration

## Purpose
E13C found that the frozen LMO source subset passes every pooled E13B/E13C execution gate at net floor 1.00% / 36h, but misses the era gate solely because 2022 PF is 1.133 versus the frozen 1.15 floor. E13D performs one final, tightly bounded local exit refinement around that coordinate.

This is explicitly the final target/hold/source tuning experiment in this lineage. If no full passer is found, stop this tuning lineage.

## Frozen source subset
LMO only:
- L = E12L 00:00–01:00 WIB `EFF_LOW__RANGE_HIGH`, LB30.
- M = E12M 01:00–02:00 WIB `EFF_HIGH__RV_LOW`, LB240.
- O = E12O 03:00–04:00 WIB `RV_HIGH__RANGE_MID`, LB360.

E12K 23:00–00:00 is excluded. No other source may enter E13D.

## Execution semantics
- ETHUSDT LONG only.
- Development only; OOS / external / reference-validation remain closed.
- One active position maximum.
- Signals arriving while busy are skipped permanently.
- Entry price is the causal 5m bar open, unchanged from E12/E13A-C.
- Exit at the first completed 5m close whose net PnL after the frozen $0.75 fee reaches the candidate profit floor.
- If not reached, force-close at the candidate max hold.
- Full possible timeout path must remain inside Development before entry is accepted.
- $500 fixed notional.
- No SHORT, no stop-loss search, no wick/intrabar target, no sizing/leverage optimization.

## Frozen local grid
Net profit floors, as percentage of fixed notional:
- 0.75% = $3.75 net
- 1.00% = $5.00 net
- 1.25% = $6.25 net
- 1.50% = $7.50 net

Max holds:
- 1440m = 24h
- 2160m = 36h
- 2880m = 48h

Exactly **12 candidates**.

## Metrics
Persist for each candidate:
- signals, accepted trades, busy skips;
- WR, timeout rate;
- net PnL, expectancy, PF, max DD, max loss streak;
- duration mean/median/p75/p90;
- 2022/2023/2024 N, WR, net, expectancy, PF;
- accepted counts by L/M/O source.

Persist exact trade ledger and source breakdown only for a formal passer selected by ranking.

## Frozen promotion gates
Identical to E13B/E13C.

### Pooled
- accepted trades >=150;
- WR >=70%;
- net PnL >0;
- expectancy >=$0.50/trade;
- PF >=1.30;
- max DD <=$125;
- max loss streak <=6;
- timeout rate <=30%.

### Cross-era
For each 2022, 2023, 2024:
- accepted trades >=40;
- WR >=65%;
- net PnL >0;
- expectancy >0;
- PF >=1.15.

At least two of three years must have WR >=70%.

## Frozen ranking among passers
1. highest minimum yearly expectancy;
2. lower max DD;
3. higher PF;
4. higher pooled expectancy;
5. higher WR;
6. lower timeout rate;
7. lower p90 duration;
8. lower max hold;
9. lower profit floor as final deterministic tie-break.

## Stop rule
If no candidate passes, this target/hold/source tuning lineage stops. Do not create E13E by further narrowing Development thresholds. The next research phase must change the scientific question, e.g. a preregistered structural-risk filter or SHORT discovery.

If a candidate passes, persist it as a Development execution candidate only. Do not open OOS without a separate preregistered validation experiment.
