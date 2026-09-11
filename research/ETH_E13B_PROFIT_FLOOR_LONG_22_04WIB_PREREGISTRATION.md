# ETH E13B — Sequential LONG Minimum-Profit-Floor Discovery Preregistration

## Purpose
E13A showed that the exact rule "close at the first completed 5m close with net PnL > $0" creates very high WR but negative expectancy because typical winners are too small relative to rare timeout losses. E13B therefore tests whether a **minimum realized net-profit floor** can repair payoff quality while preserving the one-position sequential execution constraint.

E13A remains formally FAIL. E13B is a new experiment and does not alter any E12/E13A verdict.

## Frozen scope
- Pair ETHUSDT, LONG only.
- Development only. OOS / external / reference-validation remain closed.
- Search window remains **22:00–04:00 WIB**.
- One active position maximum; signals arriving while busy are skipped permanently.
- Re-arm only after causal close.
- Entry universe: **FORMAL_ONLY** E12 characters only, because E13A showed that adding E12J/E12N near-miss hours worsened every tested sequential candidate.
- Entry characters remain exactly:
  1. 23:00–00:00 WIB `DRIVE_UP__STR_B60_80`, LB60.
  2. 00:00–01:00 WIB `EFF_LOW__RANGE_HIGH`, LB30.
  3. 01:00–02:00 WIB `EFF_HIGH__RV_LOW`, LB240.
  4. 03:00–04:00 WIB `RV_HIGH__RANGE_MID`, LB360.
- Entry at the 5m bar open exactly as E12/E13A.
- $500 notional; $0.75 frozen round-trip fee.
- No SHORT, no stop-loss search, no wick/intrabar TP assumption.

## Profit-floor semantics
For each accepted LONG:
1. Inspect completed 5m closes only, chronologically.
2. At each completed close compute net PnL after the frozen $0.75 fee.
3. Exit at the first completed close where net PnL is **at least the preregistered profit floor**.
4. If the profit floor is never reached by the preregistered max-hold horizon, force-close at that horizon and record `TIMEOUT`.
5. Signals while the position is open are ignored.
6. Full possible timeout path must remain inside Development before an entry is accepted.

## Profit-floor grid
Profit floor is expressed as a percentage of the fixed $500 notional and converted to a minimum net-dollar PnL:
- 0.10% = $0.50 net
- 0.20% = $1.00 net
- 0.30% = $1.50 net
- 0.50% = $2.50 net
- 0.75% = $3.75 net
- 1.00% = $5.00 net
- 1.50% = $7.50 net

## Max-hold grid
- 240m
- 480m
- 720m
- 960m
- 1440m
- 2160m
- 2880m

Exactly **49 Development candidates** = 7 profit floors × 7 max holds.

## Metrics
Persist for every candidate:
- candidate signals, accepted trades, busy skips, acceptance rate;
- WR, timeout rate;
- net PnL, expectancy, PF, max DD, max loss streak;
- mean / median / p75 / p90 duration;
- mean timeout PnL;
- 2022/2023/2024 N, WR, net, expectancy, PF;
- accepted trade counts by E12 source character.

Persist the exact accepted trade ledger and source breakdown only for the formally selected Development passer.

## Frozen E13B promotion gate
### Pooled sequential gate
- accepted trades >= 150;
- WR >= 70%;
- net PnL > 0;
- expectancy >= $0.50/trade;
- PF >= 1.30;
- max DD <= $125;
- max loss streak <= 6;
- timeout rate <= 30%.

### Cross-era gate
For each 2022, 2023, 2024:
- accepted trades >= 40;
- WR >= 65%;
- net PnL > 0;
- expectancy > 0;
- PF >= 1.15.

At least two of the three years must have WR >= 70%.

## Frozen ranking among formal passers
1. highest minimum yearly expectancy;
2. lowest max DD;
3. highest PF;
4. highest pooled expectancy;
5. highest WR;
6. lowest timeout rate;
7. lower p90 duration;
8. lower max hold;
9. lower profit floor as deterministic final tie-break.

If no candidate passes, report the full 49-row grid and the failure mechanism without relaxing gates.

## Interpretation boundary
E13B tests completed-close minimum-profit floors only. It does not optimize intrabar limit TP, stop-loss, sizing/leverage, SHORT, or live deployment. A passing Development candidate remains research-only until separately validated.
