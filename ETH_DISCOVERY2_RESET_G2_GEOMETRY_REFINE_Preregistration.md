# ETH Discovery 2 Reset — G2 Boundary Geometry Refinement Preregistration

**PREREGISTERED before result-bearing execution.**

## Parent evidence
G1 pair-native coarse discovery was SUPPORTED and selected:
- LONG;
- reference start 01:30 UTC (08:30 WIB);
- reference duration 180m;
- execution horizon 480m;
- Development continuation 86.2%, External 81.0%, Reference Validation 88.9%.

However, G1 selected the **minimum** reference duration and **maximum** execution horizon in the coarse grid. G2 is therefore a prespecified boundary-refinement milestone, not a rescue of a failed result.

## Scientific question
> Does the supported G1 ETH region localize to a stable shorter-reference / longer-execution neighborhood, and what pair-native coordinates should be frozen before rediscovering downstream structure and entry?

## Frozen dimensions
Direction is frozen LONG because G1 independently selected and replicated LONG. No SHORT switching in G2.

Reference-start clock:
- 00:30 UTC
- 01:00 UTC
- 01:30 UTC
- 02:00 UTC
- 02:30 UTC

Reference duration:
- 60m
- 90m
- 120m
- 150m
- 180m
- 210m
- 240m
- 270m

Execution horizon immediately following reference:
- 420m
- 480m
- 540m
- 600m
- 660m
- 720m

Total Development candidates: 5 × 8 × 6 = **240**.

No entry, retest, TP, SL, fee, PnL, leverage, or old Z5 L06 logic is used.

## Structural event grammar
Exactly the G1 pair-native LONG structural diagnostic is frozen:
- H/L from the reference window;
- strict breakout evaluated before touch counting;
- first valid HIGH-side touch with zero prior LOW-side touch is the signal;
- contiguous touch bars form one visit;
- later strict close >H is same-side continuation;
- later strict close <L is opposite invalidation;
- ambiguous both-boundary inside-close bars are unresolved/ambiguous;
- no later signal after a pre-signal strict breakout.

## Development gates
Candidate must satisfy:
- >=80 signals;
- continuation rate >=76%;
- resolved same-side rate >=81%;
- Wilson 95% lower bound >=66%;
- >=3/4 chronological Development blocks each with >=15 signals, continuation >=68%, and resolved >=75%.

## Local refinement stability
One-step neighbors within this G2 grid:
- clock ±30m;
- reference duration ±30m;
- execution horizon ±60m.

A neighbor is supportive if:
- >=60 signals;
- continuation >=72%;
- resolved >=78%.

Candidate requires >=60% of available one-step neighbors supportive, with at least 3 supportive neighbors when >=5 are available and at least 2 otherwise.

## Development-only selection
Among eligible stable candidates select lexicographically:
1. highest Wilson 95% lower bound;
2. highest minimum qualified Development-block continuation;
3. highest continuation rate;
4. highest resolved same-side rate;
5. highest signal count;
6. shortest median signal-to-continuation;
7. lower total geometry span;
8. earlier clock;
9. shorter reference duration;
10. shorter execution horizon.

External and Reference Validation remain invisible to selection.

## Historical replication
Freeze the Development-selected G2 coordinates unchanged.

Both External and Reference Validation independently must satisfy:
- >=40 signals;
- continuation >=72%;
- resolved same-side >=80%;
- same-side continuation > opposite invalidation;
- Wilson 95% lower bound >=60%.

No pooled rescue and no second-best holdout switching.

## Boundary rule
If the Development-selected candidate is on either newly expanded boundary:
- reference duration = 60m or 270m; or
- execution horizon = 420m or 720m; or
- clock = 00:30 or 02:30 UTC,
then even if historical replication passes, status is **SUPPORTED_BUT_BOUNDARY_UNRESOLVED** and downstream structure/entry discovery must not automatically freeze that exact coordinate without an explicit scientific decision.

If the selected candidate is interior and both holdouts pass, status is **SUPPORTED_AND_LOCALIZED**.

## Scientific boundary
Only a localized supported geometry authorizes downstream structure discovery. Previous ETH Z2/Z3 structure and Z5 L06 entry remain historical comparators only.

Research/shadow only. No live promotion.
