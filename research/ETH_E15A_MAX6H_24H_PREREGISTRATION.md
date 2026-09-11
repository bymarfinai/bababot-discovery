# ETH E15A — 24H LONG Character Rediscovery, Max Hold 6h

**Status:** preregistered before result inspection. Development-only. OOS CLOSED.

## Question
Can ETH's 24-hour LONG character map be rediscovered with native payoff horizons capped at 6 hours, so overlapping capital occupancy is reduced without relaxing the E12 scientific gates?

## Frozen scope
- Pair: ETHUSDT 5m
- Direction: LONG only
- Development years: 2022, 2023, 2024
- OOS: closed
- Notional: $500
- Fee: $0.75/trade
- Hours: all 24 WIB hours, one hour at a time
- Anchors per hour: HH:00, HH:15, HH:30, HH:45
- Rules: same frozen 90-rule E12 grammar
- Lookbacks: 15, 30, 60, 120, 240, 360 minutes
- Holds: **60, 120, 240, 360 minutes only**
- Candidates/hour: 90 x 6 x 4 = 2,160
- No TP/SL, no profit floor, no early exit, no SHORT, no DCA, no sequential selector in this character phase.

## Gates
Identical to E12.

Anchor supportive iff N>=40, WR>=52%, net>0, exp>0, PF>=1.05, DD<=$125, max loss streak<=10.
Hour anchor gate: evaluable>=3 and supportive>=3.
Pooled gate: N>=160, WR>=55%, net>0, exp>=+$0.50/trade, PF>=1.20, DD<=$125, max loss streak<=8.
Era gate: each 2022/2023/2024 N>=40, WR>=52%, net>0, exp>0, PF>=1.05; at least 2 eras WR>=55%.
Formal PASS requires anchor + pooled + era gates.

## Ranking among formal passers
1. min-year expectancy desc
2. supportive anchors desc
3. expectancy desc
4. WR desc
5. PF desc
6. DD asc
7. max loss streak asc
8. hold asc
9. lookback asc
10. rule name

## Interpretation
This is a fresh rediscovery under a different hold family. It must not simply filter old E12 winners. A previously FAIL hour may become PASS and a previously PASS hour may fail when H720/H960 are unavailable.

No OOS exposure and no live authorization are permitted by this experiment.