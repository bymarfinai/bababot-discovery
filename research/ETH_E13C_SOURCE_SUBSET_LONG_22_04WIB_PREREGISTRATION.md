# ETH E13C — Sequential LONG Source-Subset Discovery Preregistration

## Purpose
E13B showed that one-position execution becomes economically positive once the completed-close profit floor is increased, but the cleanest balanced coordinate still misses the frozen PF/DD gates and has weak 2022 PF. E13C tests whether this remaining weakness comes from combining all four E12 formal hour-native LONG characters into one executor.

This is a new experiment. E12 and E13A/E13B verdicts remain unchanged.

## Frozen execution coordinate
No target or hold tuning is allowed in E13C.
- Net profit floor: **1.00% of $500 notional = $5.00 net PnL**.
- Maximum hold: **2160m = 36h**.
- Exit: first completed 5m close with net PnL >= $5.00 after the frozen $0.75 round-trip fee; otherwise force-close at 36h.
- One active LONG maximum; signals arriving while busy are skipped permanently.
- Re-arm only after close.
- Entry at the same causal 5m open used in E12/E13A/E13B.
- Full possible 36h path must remain inside Development before entry is accepted.

## Source universe
Exactly the four E12 formal LONG characters inside the 22:00–04:00 WIB execution region:
- K = 23:00–00:00 WIB `DRIVE_UP__STR_B60_80`, LB60.
- L = 00:00–01:00 WIB `EFF_LOW__RANGE_HIGH`, LB30.
- M = 01:00–02:00 WIB `EFF_HIGH__RV_LOW`, LB240.
- O = 03:00–04:00 WIB `RV_HIGH__RANGE_MID`, LB360.

E13C tests **all 15 non-empty subsets** of {K,L,M,O}. No E12 near-miss source is allowed.

## Partition and economics
- ETHUSDT LONG only.
- Development only; OOS / external / reference-validation remain closed.
- $500 fixed notional.
- $0.75 fixed round-trip fee.
- No SHORT.
- No stop-loss search.
- No leverage/sizing optimization.
- No intrabar/wick TP assumption.

## Metrics
For every subset persist:
- subset identity and source count;
- candidate signals, accepted trades, busy skips, acceptance rate;
- WR, timeout rate;
- net PnL, expectancy, PF, max DD, max loss streak;
- mean/median/p75/p90 duration;
- 2022/2023/2024 N, WR, net, expectancy, PF;
- accepted count by included source.

Persist the exact trade ledger/source breakdown only for a formal Development passer selected by the frozen ranking.

## Frozen promotion gates
Use the **same gates as E13B**, unchanged.

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

## Frozen ranking among formal passers
1. highest minimum yearly expectancy;
2. greater source breadth (more included formal hour characters);
3. lower max DD;
4. higher PF;
5. higher pooled expectancy;
6. higher WR;
7. lower timeout rate;
8. lower p90 duration;
9. lexicographically smaller subset label as final deterministic tie-break.

If no subset passes, report all 15 rows and failure mechanisms; do not alter the frozen 1.00% / 36h coordinate.

## Interpretation boundary
A passing source subset would mean only that, within Development, a particular combination of already-formal E12 entry characters is more suitable for one-position sequential execution at the frozen E13B near-miss exit coordinate. It would not authorize OOS or live deployment.
