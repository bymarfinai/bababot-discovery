# ETH Discovery 2 Reset — G3 Temporal Decomposition Preregistration

**PREREGISTERED before result-bearing execution.**

## Parent evidence
G1 found a new pair-native ETH LONG region. G2 refined that region to reference start 01:00 UTC with a 150-minute reference, but its monolithic execution window selected the 720-minute upper boundary.

Post-run timing anatomy showed that 720 minutes conflated two different processes:
- waiting for the first valid setup signal; and
- allowing an already-known signal to resolve.

Median signal-to-continuation was only 25m Development, 20m External, and 15m Reference Validation, while signal arrival itself was much more dispersed.

## Scientific question
> What setup-acquisition window and post-signal follow-through horizon are native to the supported ETH LONG geometry when those two clocks are separated causally?

## Frozen reference geometry
- Pair: ETHUSDT.
- Side: LONG.
- Reference start: 01:00 UTC (08:00 WIB).
- Reference duration: 150 minutes.
- Reference ends / setup acquisition begins: 03:30 UTC (10:30 WIB).
- H/L/R are computed only from the frozen 150-minute reference.

No previous Z2/Z3 retest rule, Z5 L06 entry, TP, SL, fee, PnL, leverage, or sizing is used.

## Frozen temporal grid
Setup acquisition window after reference end:
- 120m
- 180m
- 240m
- 300m
- 360m
- 420m
- 480m

Post-signal follow-through horizon after the completed signal becomes known:
- 60m
- 90m
- 120m
- 180m
- 240m
- 300m

Total Development candidates = **42**.

## Signal grammar
Within the setup-acquisition window:
- strict close >H or <L is evaluated before touch counting;
- the first valid HIGH touch while the completed close remains inside/on the range is the LONG pressure signal only if no LOW visit occurred earlier;
- if a LOW visit occurs first, the session can never become an OPP0 LONG signal;
- an inside-close bar touching both H and L is ambiguous and cannot signal;
- a pre-signal strict breakout closes the acquisition attempt and no later signal is allowed;
- signal timestamp is the close of the completed 5m signal bar.

## Follow-through grammar
After the completed signal is known, evaluate only bars beginning at or after signal timestamp for the frozen follow-through horizon:
- first strict close >H = SAME_SIDE continuation;
- first strict close <L = OPPOSITE invalidation;
- first inside-close both-boundary bar = AMBIGUOUS;
- if none occurs by follow-through end = NO_BREAK.

The signal bar itself cannot be reused as a post-signal outcome bar.

## Session inclusion
A candidate session is included only when:
- execution-start weekday is Monday-Friday;
- the full reference + maximum candidate acquisition/follow-through requirement for that candidate is inside one historical partition;
- all required 5m bars are present.

## Development metrics
For every acquisition/follow pair report:
- complete sessions;
- signals and signal rate;
- SAME_SIDE / OPPOSITE / AMBIGUOUS / NO_BREAK counts;
- continuation rate among all signals;
- resolved same-side rate;
- Wilson 95% lower bound;
- median signal delay from acquisition start;
- median signal-to-continuation delay;
- 4 chronological Development block metrics.

## Development gate
Candidate must satisfy:
- >=100 signals;
- continuation rate >=70%;
- resolved same-side rate >=82%;
- Wilson 95% lower bound >=62%;
- >=3/4 Development blocks each with >=15 signals, continuation >=65%, resolved >=75%.

## Local temporal stability
One-step neighbors are acquisition ±60m where present and follow-through adjacent listed horizon.
A neighbor is supportive if:
- >=80 signals;
- continuation >=66%;
- resolved >=78%.

Candidate requires at least 60% of available neighbors supportive and at least 2 supportive neighbors.

## Development-only selection
Among eligible stable candidates select lexicographically:
1. highest Wilson 95% lower bound;
2. highest minimum qualified Development-block continuation;
3. highest continuation rate;
4. highest resolved same-side rate;
5. highest signal count;
6. shorter follow-through horizon;
7. shorter acquisition window.

External and Reference Validation are invisible to selection.

## Historical replication
Freeze selected acquisition and follow-through horizons unchanged.
Both External and Reference Validation independently must satisfy:
- >=40 signals;
- continuation >=68%;
- resolved same-side >=78%;
- same-side continuation > opposite invalidation;
- Wilson 95% lower bound >=55%.

No pooled rescue, no switching to another acquisition/follow pair after holdout inspection, and no gate relaxation.

## Scientific boundary
If G3 is supported, the ETH temporal structure is considered localized enough to proceed to a separate downstream **structure-sequence discovery** milestone. Entry discovery still comes later and old L06 must compete again rather than being promoted automatically.

Research/shadow only. No live promotion.
