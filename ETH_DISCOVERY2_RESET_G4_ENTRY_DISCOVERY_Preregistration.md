# ETH Discovery 2 Reset — G4 ETH-Native Entry Discovery Preregistration

**PREREGISTERED before result-bearing execution.**

## Frozen parent
G4 inherits the historically supported G2+G3 lineage unchanged:
- ETHUSDT Binance Futures raw 5m;
- direction **LONG**;
- reference start **01:30 UTC (08:30 WIB)**;
- reference duration **180m**;
- execution horizon **720m**;
- reference **01:30–04:30 UTC / 08:30–11:30 WIB**;
- execution **04:30–16:30 UTC / 11:30–23:30 WIB**;
- frozen G2 first HIGH-side pressure signal;
- frozen G3 downstream structure = **DIRECT B00**, the first strict completed 5m close above H after the pressure signal, before structural invalidation.

No old Z2/Z3 retest prerequisite is inherited. Old Z5 L06 is only a named historical control and must re-earn selection.

## Scientific question
> After a valid frozen DIRECT B00, should ETH be entered immediately at the next executable 5m open, or does a shallow resting pullback with pair-native price and patience improve entry quality enough to compensate for missed fast breakouts?

G4 is still **entry geometry only**. There is no TP, SL, leverage, fee, dollar PnL, PF, or live promotion.

## Data partitions
Reuse the frozen historical partitions:
- External: 2020-01-01 to 2022-01-01;
- Development: 2022-01-01 to 2025-01-01;
- Reference Validation: 2025-01-01 to 2026-07-30.

August 2026 remains descriptive only. Development selects exactly one entry candidate. External and Reference Validation remain closed until selection is frozen.

## Causal timing convention
A 5m bar indexed at time `t` is known only after its completion at `t+5m`.

For a B00 completed at `T`:
- the entry decision is first available at `T`;
- NEXT_OPEN enters at the open of the 5m bar beginning at `T`;
- resting limits are placed at `T` and may fill only from that bar onward.

No candidate uses information from a bar before that information is completed.

## Candidate family
### Immediate control
- **NEXT_OPEN**: buy at the open of the first 5m bar after the completed B00.

### Resting pullback family
Limit price:

`P(q) = H + qR`

Frozen q grid:
- q = 0.00
- 0.02
- 0.04
- **0.06** ← exact historical Z5 price control
- 0.08
- 0.10
- 0.12

Frozen maximum order lives:
- **5m**
- **15m**
- **30m** ← exact historical Z5 patience control when paired with q=0.06
- **60m**

Total candidates = **1 NEXT_OPEN + 7×4 limits = 29**.

`q=0.12` and `wait=60m` are explicit upper sentinels. `q=0.00` is the natural H boundary; q<0 would be an inside-range entry and is a different structural family. `wait=5m` is the minimum resolution available on the frozen 5m data.

## Limit fill mechanics
For each resting limit after B00:
1. If a candidate bar opens at or below the limit, fill at that bar open (`OPEN_PRICE_IMPROVEMENT`).
2. Otherwise, if that bar low trades at or below the limit, fill at the limit (`INTRABAR_LIMIT`).
3. If a completed bar closes below H before any fill, cancel as `CLOSE_BELOW_H_BEFORE_FILL`.
4. If no fill occurs before the preregistered order life expires, cancel as `NO_FILL_WITHIN_WINDOW`.
5. Orders never extend beyond the frozen G2 execution end.

For an intrabar limit fill, high/low ordering inside the 5m bar is unknowable. Therefore the fill bar itself is never credited with a target extension. If that fill bar closes below H, it is a conservative immediate structural failure.

For an open-price fill / NEXT_OPEN, the fill occurs before that bar's later path. A same-bar target touch plus close below H is treated conservatively as ambiguous and **not** counted as success.

## Entry-relative clean extension metrics
For a filled entry price E, define clean extensions:
- E05: high reaches `E + 0.05R` before a completed close below H;
- E10: high reaches `E + 0.10R` before a completed close below H;
- E20: high reaches `E + 0.20R` before a completed close below H.

Evaluation ends at the frozen execution end. Same-bar target/re-entry ambiguity is not success.

These targets are measured from the actual executable entry price, not from B00 or H, so lower fills must still generate new movement after entry.

## Reported metrics
Per candidate and partition:
- B00 cases;
- filled entries;
- fill participation;
- median entry excess `(E-H)/R`;
- median entry improvement versus NEXT_OPEN `(NEXT_OPEN-E)/R`;
- conditional E05/E10/E20 rates among filled entries;
- effective E10 and E20 = successes / all frozen B00 cases, so unfilled missed breakouts are economically visible as opportunity cost;
- Wilson 95% lower bound for effective E10;
- median B00→fill minutes;
- median fill→E10 minutes among E10 successes;
- close-below-H failures before E10.

## Development chronological stability
Chronologically sort frozen B00 cases and split into four near-equal blocks.

For each candidate, each block reports:
- B00 N;
- fill participation;
- effective E10;
- effective E20.

A positive block requires:
- >=35 B00 cases;
- fill participation >=45%;
- effective E10 >=30%;
- effective E20 >=18%.

## Development gate
A candidate must satisfy ALL:
- >=100 filled entries;
- fill participation >=55%;
- conditional E10 >=50%;
- conditional E20 >=35%;
- effective E10 >=35%;
- effective E20 >=22%;
- Wilson 95% lower bound for effective E10 >=28%;
- >=3 of 4 positive chronological blocks.

For resting limits only:
- median entry improvement versus NEXT_OPEN must be >= **+0.005R**.

NEXT_OPEN is exempt from the improvement requirement because it is the executable baseline.

## Local entry-coordinate stability
NEXT_OPEN has no tunable coordinate and requires no neighbor test.

A resting-limit candidate's orthogonal neighbors are:
- immediately adjacent q values at the same wait;
- immediately adjacent wait values at the same q.

A neighbor is supportive if it has:
- >=80 fills;
- participation >=45%;
- effective E10 >=30%;
- effective E20 >=18%.

A resting-limit candidate must have at least **2 supportive available neighbors**, or all available neighbors if fewer than 2 exist. This blocks isolated price×patience spikes.

## Development-only selection
Among candidates passing the Development gate and applicable stability gate, rank lexicographically by:
1. highest Wilson 95% lower bound for effective E10;
2. highest effective E20;
3. highest effective E10;
4. highest conditional E20;
5. highest median entry improvement versus NEXT_OPEN;
6. highest fill participation;
7. shortest maximum order life;
8. simplest deterministic tie-break: NEXT_OPEN first; otherwise lower q first.

External and Reference Validation are not read during candidate selection.

## Boundary rule
If the selected resting-limit candidate has **q=0.12** or **wait=60m**, the family remains boundary-open:
- status = `ETH_DISCOVERY2_RESET_G4_ENTRY_BOUNDARY_OPEN`;
- holdouts remain closed;
- no post-hoc extrapolation or second-best substitution.

q=0.00 and wait=5m are natural closed boundaries, not open sentinels.

## Historical replication
Freeze the Development-selected candidate unchanged.

Each independent holdout must satisfy:
- >=40 filled entries;
- participation >=45%;
- conditional E10 >=45%;
- conditional E20 >=30%;
- effective E10 >=30%;
- effective E20 >=18%;
- Wilson 95% lower bound for effective E10 >=20%.

For a resting limit, median improvement versus NEXT_OPEN must remain >=0.

Both External and Reference Validation must pass. Pooled holdout is descriptive only and cannot rescue an individual failure.

## Decision rules
- no Development candidate -> `ETH_DISCOVERY2_RESET_G4_NO_DEV_CANDIDATE`;
- selected upper sentinel -> `ETH_DISCOVERY2_RESET_G4_ENTRY_BOUNDARY_OPEN`;
- selected candidate fails either holdout -> `ETH_DISCOVERY2_RESET_G4_CANDIDATE_NOT_REPLICATED`;
- both holdouts pass -> `ETH_DISCOVERY2_RESET_G4_SUPPORTED`.

A SUPPORTED G4 freezes entry geometry only. Economics must still be rediscovered afterward on the frozen G2+G3+G4 lineage.

Research/shadow only. No live promotion.
