# ETH Discovery 2 Reset — G1 Scientific Verdict

**Verdict: SUPPORTED.**

G1 discarded the previous ETH Z1 fixed 330m reference + 390m execution geometry as a privileged parent and performed a fresh pair-native coarse search over:
- 48 half-hour UTC reference starts;
- reference durations 180/240/300/360/420 minutes;
- execution horizons 240/300/360/420/480 minutes;
- LONG and SHORT mirrored first-side liquidity-pressure structure.

Total Development search: **1,200 geometries × 2 directions = 2,400 directional candidates**.

## Development-selected geometry
**LONG / reference start 01:30 UTC (08:30 WIB) / reference 180m / execution 480m**

Execution begins at **04:30 UTC (11:30 WIB)** and ends at **12:30 UTC (19:30 WIB)**.

Development:
- Signals: 196.
- Same-side continuation rate: **86.2%**.
- Resolved same-side rate: **93.9%**.
- Wilson 95% lower bound: **80.7%**.
- Median signal to continuation: **20 minutes**.
- Local supportive neighbors: **4/4**.
- Positive Development blocks: **4/4**.
- Block continuation: 80.9%, 85.7%, 91.4%, 85.7%.

## Historical replication
External:
- Signals: 100.
- Continuation: **81.0%**.
- Resolved same-side: **88.0%**.
- Wilson LB: **72.2%**.
- Same/opposite: 81/11.
- **PASS**.

Reference Validation:
- Signals: 99.
- Continuation: **88.9%**.
- Resolved same-side: **92.6%**.
- Wilson LB: **81.2%**.
- Same/opposite: 88/7.
- **PASS**.

## Key scientific finding
The pair-native reset did **not** reproduce the inherited ETH Z1 geometry. It selected a materially different reference/execution structure: a much shorter 180-minute reference followed by a longer 480-minute observation/execution horizon, with LONG as the supported direction.

This directly supports the project rule: **copy the discovery grammar, never copy the coordinates.**

## Boundary condition
The selected reference duration is the **minimum** of the G1 search grid (180m) and the selected execution horizon is the **maximum** (480m). Therefore the exact pair-native coordinates are not yet considered fully localized. A separate preregistered boundary-refinement experiment is scientifically warranted before downstream structure/entry discovery.

G1 validates geometry and directional pressure only. It does not promote old Z2/Z3 rules, old Z5 L06 entry, TP/SL, or economics.

Research/shadow only. No live promotion.
