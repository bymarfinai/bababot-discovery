# ETH Discovery 2 Reset — S1 Auction-Repair Sequence Preregistration

**PREREGISTERED before result-bearing execution.**

## Parent
Frozen G3 temporal parent:
- ETHUSDT LONG;
- reference 01:00-03:30 UTC (08:00-10:30 WIB), 150 minutes;
- setup acquisition 03:30-05:30 UTC, maximum 120 minutes;
- G3 signal = first valid HIGH-side touch with zero prior LOW-side visit;
- post-signal follow-through horizon = 240 minutes from completed signal timestamp.

G3 replicated historically. Previous ETH Z2/Z3 retest rules and Z5 L06 entry are **not** parents and are not copied.

## Scientific question
> After the pair-native G3 first-touch pressure signal, does ETH have a reproducible rejection/repair/retest sequence that identifies a higher-quality continuation subset before the strict breakout occurs?

S1 is structural only. No entry price, TP, SL, fee, PnL, leverage, or sizing.

## Sequence grammar
All sequence observations begin only after the completed G3 signal bar.

Before an S1 trigger:
- a strict completed close >H means DIRECT_BREAK and the auction-repair candidate is absent for that session;
- a strict completed close <L means INVALIDATED and the candidate is absent;
- an inside-close bar touching both H and L is AMBIGUOUS and the candidate is absent.

An auction-repair candidate requires, in causal order:
1. G3 HIGH-side signal is completed;
2. price demonstrates a completed rejection/leave condition below H according to a frozen depth mode;
3. after that rejection is known, price returns to H with an inside/on-range completed close (`high >= H` and `close <= H` and `close >= L`), creating the S1 retest trigger;
4. the retest trigger must occur within the candidate's frozen maximum retest-wait measured from G3 signal timestamp and before any strict breakout/invalidation.

The trigger timestamp is the close of the retest bar. The trigger bar cannot also be reused as the post-trigger outcome bar.

## Frozen rejection-depth family
Depth is normalized to the pair-native reference range R=H-L.

- `D00_LEAVE`: at least one completed post-signal bar no longer touches H (`high < H`) while closing inside the range. This is a pure separated-visit condition with no depth threshold.
- `D02_CLOSE`: completed close <= H - 0.02R.
- `D05_CLOSE`: completed close <= H - 0.05R.
- `D10_CLOSE`: completed close <= H - 0.10R.
- `D15_CLOSE`: completed close <= H - 0.15R.

No 95%/90% Fibonacci-style threshold from the old ETH lineage is copied.

## Frozen maximum retest wait
Measured from completed G3 signal timestamp to completed S1 retest-trigger timestamp:
- 30m
- 60m
- 90m
- 120m

Total selectable sequence candidates = 6? No: 5 depth modes × 4 wait horizons = **20** candidates.

`G3_SIGNAL_ONLY` is reported as a non-selectable benchmark.

## Post-trigger structural outcome
From the first raw 5m bar after the completed retest trigger until the earlier of:
- G3 signal timestamp + 240m; or
- first terminal event,
classify:
- SAME_SIDE: first strict completed close >H;
- OPPOSITE: first strict completed close <L;
- AMBIGUOUS: first inside-close bar touching both boundaries;
- NO_BREAK: none before horizon end.

## Metrics
For each candidate and historical partition:
- G3 source signals;
- S1 available triggers;
- participation = triggers / G3 source signals;
- SAME_SIDE / OPPOSITE / AMBIGUOUS / NO_BREAK counts;
- continuation rate = SAME_SIDE / triggers;
- resolved same-side rate = SAME_SIDE / (SAME_SIDE + OPPOSITE);
- Wilson 95% lower bound of continuation rate;
- median signal-to-rejection minutes;
- median rejection-to-retest minutes;
- median trigger-to-continuation minutes;
- four chronological Development blocks and their participation/continuation.

## Development candidate gate
A candidate must satisfy all:
- >=35 triggers;
- participation >=28%;
- continuation >=78%;
- resolved same-side >=86%;
- Wilson 95% lower bound >=65%;
- >=3/4 chronological Development blocks each with >=7 triggers, continuation >=70%, and resolved same-side >=80%.

## Local stability
One-step neighbors are:
- adjacent depth mode in the listed order at the same wait horizon;
- adjacent wait horizon at the same depth mode.

A neighbor is supportive if:
- >=28 triggers;
- participation >=22%;
- continuation >=72%;
- resolved same-side >=82%.

Candidate requires at least 60% of available neighbors supportive and at least 2 supportive neighbors when 3+ neighbors exist; at least 1 when only 1-2 neighbors exist.

## Development-only selection
Among eligible locally stable candidates select lexicographically:
1. highest Wilson lower bound;
2. highest minimum qualified Development-block continuation;
3. highest continuation rate;
4. highest resolved same-side rate;
5. highest participation;
6. higher trigger count;
7. shorter maximum retest wait;
8. shallower rejection depth in the listed order.

External and Reference Validation are invisible to selection.

## Historical replication
Freeze the selected depth mode and wait horizon unchanged.

Both External and Reference Validation independently must satisfy:
- >=18 triggers;
- participation >=22%;
- continuation >=70%;
- resolved same-side >=80%;
- SAME_SIDE > OPPOSITE;
- Wilson 95% lower bound >=52%.

No pooled rescue, no switching candidate after holdout inspection, no threshold relaxation.

## Scientific boundary
SUPPORTED S1 means only that a reproducible pre-breakout auction-repair sequence exists. It authorizes a separate entry-discovery milestone comparing causal entry locations around the supported trigger. It does not authorize TP/SL/economics or automatically revive old L06.

If S1 fails, this exact rejection/retest family is closed and the next structure experiment must use a different mechanism such as direct acceptance rather than nearby depth tuning.

Research/shadow only. No live promotion.
