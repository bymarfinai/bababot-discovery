# ETH Discovery 2 Reset — G2 Scientific Verdict

**Verdict: SUPPORTED.**

G2 refined the duration boundaries around the supported G1 ETH-native clock/side without changing the structural pressure-event grammar or preregistered Development/replication gates.

## Frozen parent from G1
- Direction: **LONG**.
- Reference start: **01:30 UTC (08:30 WIB)**.
- G1 coarse duration coordinate: **R180 / E480**.

G1 had selected R180 at its minimum reference boundary and E480 at its maximum execution boundary, so those duration coordinates were not yet fully localized.

## G2 preregistered refinement
Development-only grid:
- reference durations: 60/90/120/150/180/210/240/270/300m;
- execution horizons: 300/360/420/480/540/600/660/720/780m;
- total: **81 duration geometries**;
- R60/R300 and E300/E780 served as explicit outer sentinels and remained eligible for ranking.

A winner could be declared localized only if it was strictly inside all four outer sentinel boundaries. External and Reference Validation were opened only after Development selection and localization.

## Development-selected geometry
**LONG / 01:30 UTC / R180 / E720**

Timing:
- Reference: **01:30–04:30 UTC (08:30–11:30 WIB)**.
- Execution: **04:30–16:30 UTC (11:30–23:30 WIB)**.

Development:
- Signals: **206**.
- Same-side continuation: **89.3%**.
- Resolved same-side: **91.5%**.
- Wilson 95% lower bound: **84.4%**.
- Median signal→continuation: **25 minutes**.
- Supportive one-step duration neighbors: **4/4**.
- Positive chronological Development blocks: **4/4**.
- Block continuation rates: **81.6%, 89.1%, 93.4%, 92.0%**.

The winner is strictly interior to the preregistered search sentinels, so G2's boundary-localization condition passed.

## G1 parent versus G2 winner on Development
| Geometry | Signals | Continuation | Resolved | Wilson LB | Neighbors | Blocks |
|---|---:|---:|---:|---:|---:|---:|
| G1 R180/E480 | 196 | 86.2% | 93.9% | 80.7% | 4/4 | 4/4 |
| **G2 R180/E720** | **206** | **89.3%** | **91.5%** | **84.4%** | **4/4** | **4/4** |

The refinement retained the 180-minute reference but materially extended the supported execution horizon from 480 to 720 minutes.

## Historical replication
External:
- Signals: **105**.
- Continuation: **83.8%**.
- Resolved same-side: **88.0%**.
- Wilson LB: **75.6%**.
- Same/opposite: **88/12**.
- **PASS**.

Reference Validation:
- Signals: **101**.
- Continuation: **90.1%**.
- Resolved same-side: **91.0%**.
- Wilson LB: **82.7%**.
- Same/opposite: **91/9**.
- **PASS**.

Therefore both independent historical replication gates passed unchanged.

## Local landscape
The Development leaderboard shows a broad supportive longer-horizon region rather than an isolated E720 spike. Leading R180 candidates included:
- R180/E600: 89.1% continuation, Wilson LB 84.1%, 4/4 supportive neighbors, 4/4 blocks;
- R180/E720: 89.3%, Wilson LB 84.4%, 4/4 neighbors, 4/4 blocks;
- R180/E780 sentinel: 89.0%, Wilson LB 84.0%, 3/3 neighbors, 4/4 blocks;
- R180/E660: 88.7%, Wilson LB 83.7%, 4/4 neighbors, 4/4 blocks;
- R180/E540: 88.4%, Wilson LB 83.3%, 4/4 neighbors, 4/4 blocks.

This plateau is scientifically more important than the small numerical difference between E600/E660/E720/E780: ETH's pair-native structure appears to favor a **3-hour reference followed by a substantially longer continuation horizon** than the inherited old ETH geometry.

Per the preregistered deterministic ranking, **R180/E720** is the frozen G2 coordinate.

## Scientific interpretation
G2 strengthens the reset conclusion:
1. The old ETH Z1 330m reference + 390m execution geometry should not be restored.
2. The pair-native ETH reference duration localizes at **180m** within the refined grid.
3. The continuation process is materially longer-lived than G1's initial E480 boundary suggested; the supported frozen horizon is **720m**.
4. The signal remains strongly LONG-biased and replicated across both historical holdouts.
5. The result is locally stable across neighboring duration coordinates rather than dependent on one isolated cell.

## What G2 does NOT validate
G2 validates only the ETH pair-native structural clock/side/duration geometry. It does **not** validate or inherit:
- old Z2/Z3 retest/breakout rules;
- old Z5 L06 entry;
- static TP/SL/hold rules;
- checkpoint harvesting rules;
- leverage, fees, PnL, or live economics.

The next scientifically valid stage is to rediscover downstream ETH structure on the frozen **LONG / 01:30 UTC / R180 / E720** geometry. Entry should be rediscovered only after that downstream structure replicates. Old L06 may be used only as a historical comparator, not as an inherited rule.

Research/shadow only. No live promotion.