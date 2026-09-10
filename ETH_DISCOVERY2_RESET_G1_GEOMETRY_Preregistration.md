# ETH Discovery 2 Reset — G1 Pair-Native Geometry Preregistration

**PREREGISTERED before result-bearing execution.**

## Scientific reset
This lineage explicitly does **not** treat the previous ETH Z1 5h30 reference + 6h30 execution geometry as a parent coordinate. The old lineage remains historical evidence only.

The transferable lesson from BTC/SOL is the discovery grammar:
1. define a finite structural question;
2. search Development only;
3. require local stability rather than an isolated maximum;
4. freeze the Development-selected candidate;
5. open External and Reference Validation only for replication;
6. do not rescue a failed holdout candidate;
7. only after geometry is supported, rediscover the downstream structure and entry on that geometry.

## G1 question
> What clock, reference-range duration, execution horizon, and directional side are native to ETH for first-side liquidity-pressure continuation?

No prior ETH clock, duration, side, entry, retest, TP, SL, fee, PnL, leverage, or economics is allowed to determine the winner.

## Data and partitions
- ETHUSDT Binance Futures raw 5m.
- Coverage gate >=99.5%.
- Existing frozen historical partitions are reused only to preserve honest holdouts:
  - External: 2020-01-01 to 2022-01-01.
  - Development: 2022-01-01 to 2025-01-01.
  - Reference Validation: 2025-01-01 to 2026-07-30.
- August 2026 remains descriptive only and is not used for selection or replication.
- A candidate session is included only when the full reference + execution window lies inside one partition and all expected 5m bars are present.
- Session weekday is defined by execution-start timestamp; Saturday/Sunday execution starts are excluded.

## Frozen coarse geometry search
Clock / reference start:
- all 48 half-hour UTC placements from 00:00 through 23:30.

Reference duration:
- 180m
- 240m
- 300m
- 360m
- 420m

Execution horizon immediately following the reference:
- 240m
- 300m
- 360m
- 420m
- 480m

Directional side:
- LONG = first valid HIGH-side touch before any LOW-side touch; later strict close > H is same-side continuation and strict close < L is opposite invalidation.
- SHORT = exact mirror: first valid LOW-side touch before any HIGH-side touch; later strict close < L is same-side continuation and strict close > H is opposite invalidation.

Total geometry cells = 48 × 5 × 5 = 1,200.
Total directional candidates = 2,400.

The old 330m / 390m geometry is **not** inserted into this coarse grid as a privileged coordinate. If the coarse winner later supports a local 30m refinement, that requires a separate preregistration.

## Frozen pressure-event grammar
For each reference window:
- H = maximum reference high.
- L = minimum reference low.
- R = H-L.
- strict close outside H/L is evaluated before touch counting.
- A touch requires intrabar reach of the boundary while the completed close remains inside/on the reference range.
- contiguous touching bars count as one visit until price leaves the boundary.
- LONG signal: first HIGH visit with zero prior LOW visits.
- SHORT signal: first LOW visit with zero prior HIGH visits.
- If the opposite boundary was visited first, that directional candidate has no signal for that session.
- If a strict same-side or opposite breakout occurs before the first valid signal, the session is closed for that directional candidate and cannot signal later.
- After a signal, terminal state is first strict same-side close, first strict opposite close, or NO_BREAK by execution end.
- A bar touching both boundaries while closing inside is ambiguous and terminates without a signal if no signal yet; after signal it is treated as unresolved/ambiguous rather than a target.

This grammar is a structural diagnostic, not a trading entry rule.

## Metrics per directional candidate
For Development and every historical partition independently:
- complete sessions;
- signal count and signal rate;
- same-side continuation count;
- opposite invalidation count;
- no-break/ambiguous count;
- same-side continuation rate among all signals;
- resolved same-side rate = same-side / (same-side + opposite);
- Wilson 95% lower bound of same-side continuation rate;
- median minutes from signal to same-side continuation.

## Development block stability
Development sessions for each candidate are sorted chronologically and divided into four near-equal blocks.
For each block report signal N, continuation rate, and resolved same-side rate.

A Development candidate must satisfy ALL:
- >=80 signals overall;
- same-side continuation rate >=75%;
- resolved same-side rate >=80%;
- Wilson 95% lower bound >=65%;
- >=3 of 4 Development blocks each have:
  - >=15 signals;
  - continuation rate >=68%;
  - resolved same-side rate >=75%.

## Local geometry stability
An eligible Development candidate must also be locally stable within the same directional side.
Its one-step coordinate neighbors are:
- clock ±30m at same reference duration and execution horizon;
- reference duration ±60m where present at same clock and execution horizon;
- execution horizon ±60m where present at same clock and reference duration.

Each available neighbor is a soft-support neighbor if:
- >=60 Development signals;
- continuation rate >=70%;
- resolved same-side rate >=77%.

Local-stability requirement:
- at least 60% of available one-step neighbors must be soft-support neighbors;
- minimum 3 supportive neighbors when >=5 neighbors exist;
- minimum 2 supportive neighbors when only 3-4 neighbors exist.

## Development-only selection
Among candidates that pass both the Development gate and local-stability gate, rank lexicographically by:
1. highest Wilson 95% lower bound;
2. highest minimum Development-block continuation rate among blocks with >=15 signals;
3. highest overall continuation rate;
4. highest resolved same-side rate;
5. highest signal count;
6. shortest median minutes to continuation;
7. lower total geometry span (reference + execution) as a simplicity tie-break;
8. earlier UTC clock;
9. shorter reference duration;
10. shorter execution horizon;
11. LONG before SHORT only as final deterministic tie-break.

External and Reference Validation are not read by candidate selection.

## Historical replication
Freeze the selected clock, reference duration, execution horizon, and side unchanged.

SUPPORTED requires BOTH External and Reference Validation independently to satisfy:
- >=40 signals;
- continuation rate >=70%;
- resolved same-side rate >=78%;
- same-side continuation count > opposite invalidation count;
- Wilson 95% lower bound >=58%.

Pooled holdout is descriptive only and cannot rescue a failed individual holdout.

## Scientific interpretation
A SUPPORTED G1 result establishes only a pair-native ETH structural geometry and side. It does not validate the previous Z2/Z3 retest/breakout rules, previous L06 entry, or any economic rule.

If G1 is supported, next experiment must rediscover the downstream ETH structure on top of the frozen G1 geometry. Only after downstream structure is supported may entry be rediscovered. Old Z5 L06 is a historical comparator only and must earn its place again if included later.

If G1 has no Development candidate or fails historical replication, do not relax gates and do not pick the second-best holdout result. The next experiment must change the structural family or discovery abstraction.

Research/shadow only. No live promotion.
