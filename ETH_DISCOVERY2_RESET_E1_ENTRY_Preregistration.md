# ETH Discovery 2 Reset — E1 Pair-Native Entry Preregistration

**PREREGISTERED before result-bearing execution.**

## Parent
Frozen supported G3 parent only:
- ETHUSDT LONG;
- reference 01:00-03:30 UTC = 08:00-10:30 WIB;
- reference duration 150m;
- setup acquisition 03:30-05:30 UTC = 10:30-12:30 WIB, maximum 120m;
- signal = first valid HIGH-side touch with zero prior LOW-side visit;
- signal is known at the completed 5m bar close;
- follow-through horizon = 240m from signal timestamp.

S1 auction-repair failed replication and is not used. Old Z2/Z3 structure and old Z5 `H+0.06R` entry are not used.

## Scientific question
> Once the native G3 HIGH-touch signal is causally known, where should ETH be entered so that price is improved without destroying participation or subsequent continuation?

No TP, SL, fees, leverage, PnL, sizing, or economics in E1.

## Frozen entry family
`NEXT_OPEN`:
- enter at the immediately following raw 5m bar open after the completed signal.
- non-resting benchmark but is selectable because it is a genuine causal entry candidate.

Resting buy-limit levels, normalized to pair-native R=H-L:
- `H00`: H
- `M02`: H - 0.02R
- `M05`: H - 0.05R
- `M10`: H - 0.10R
- `M15`: H - 0.15R
- `M20`: H - 0.20R

Resting-order validity windows after signal timestamp:
- 30m
- 60m

Total selectable candidates = NEXT_OPEN + 6×2 = **13**.

No old `H+0.06R` breakout limit is included.

## Fill semantics
For resting limits:
1. Order becomes active only after the completed signal is known.
2. First eligible bar starts exactly at signal timestamp.
3. If eligible bar opens at/below limit, fill at open (price improvement).
4. Else if low <= limit, fill at the fixed limit.
5. If completed close <L occurs before any fill, order is cancelled from the next bar onward.
6. If an intrabar limit fill occurs and that same bar later closes <L, the fill remains valid; post-entry outcome evaluation starts from the next raw bar to avoid unknown intrabar ordering.
7. If a strict close >H occurs before fill, the resting candidate expires as missed continuation and cannot fill later.
8. Order expires at its 30m/60m window if unfilled.

For NEXT_OPEN:
- entry is the first bar open at signal timestamp;
- that same bar is eligible for post-entry evaluation because the position exists from its open.

## Structural diagnostics after entry
Evaluation ends at signal timestamp + 240m.

Report:
- available fills;
- participation vs G3 source signals;
- median entry offset `(entry-H)/R`;
- median and p75 price improvement in R vs same-session NEXT_OPEN;
- SAME_SIDE strict close >H after entry;
- OPPOSITE strict close <L before SAME_SIDE;
- C10 = H+0.10R reach by high;
- C20 = H+0.20R reach;
- C30 = H+0.30R reach;
- median/p90 adverse excursion from actual entry in R;
- median MFE from actual entry in R;
- median minutes entry→strict continuation;
- four chronological Development source-signal blocks.

C10/C20/C30 are diagnostics only, not take-profit targets.

## Development gate
Candidate must satisfy:
- >=65 fills;
- participation >=52%;
- SAME_SIDE continuation after fill >=78%;
- resolved same-side >=86%;
- C10 reach >=58%;
- C20 reach >=42%;
- SAME_SIDE count > OPPOSITE count;
- >=3/4 Development blocks each with >=12 fills, continuation >=70%, and C20 reach >=32%.

## Local stability
For resting candidates, adjacent level and adjacent wait-window candidates are neighbors. NEXT_OPEN has no parameter neighbor and is considered structurally stable only through its Development block gate.

A resting neighbor is supportive if:
- >=55 fills;
- participation >=45%;
- continuation >=72%;
- C20 reach >=35%.

Resting candidate requires at least 60% of available neighbors supportive and at least one supportive neighbor.

## Development-only selection
Among eligible candidates rank lexicographically by:
1. highest minimum qualified Development-block C20 reach;
2. highest C30 reach;
3. highest C20 reach;
4. highest continuation rate;
5. lowest median entry offset `(entry-H)/R`;
6. lowest p90 adverse excursion R;
7. highest participation;
8. shorter resting-order window;
9. shallower resting level in order H00, M02, M05, M10, M15, M20;
10. NEXT_OPEN only by its measured metrics, not privileged.

External and Reference Validation are invisible to selection.

## Historical replication
Freeze the Development-selected entry unchanged.

Both External and Reference Validation independently must satisfy:
- >=30 fills;
- participation >=45%;
- continuation >=68%;
- resolved same-side >=78%;
- C10 reach >=48%;
- C20 reach >=32%;
- SAME_SIDE > OPPOSITE.

No pooled rescue, candidate switching, threshold relaxation, or old-L06 fallback.

## Scientific boundary
SUPPORTED E1 establishes a historically replicated causal entry on the new ETH pair-native structure. Only then may a separate money-geometry experiment be preregistered.

If E1 fails, do not tune around the holdout. The next experiment must change entry mechanism (for example breakout confirmation) rather than interpolate nearby resting levels.

Research/shadow only. No live promotion.
