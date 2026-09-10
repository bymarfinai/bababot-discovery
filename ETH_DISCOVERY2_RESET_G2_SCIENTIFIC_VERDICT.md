# ETH Discovery 2 Reset — G2 Scientific Verdict

**Verdict: SUPPORTED, BUT EXECUTION BOUNDARY UNRESOLVED.**

G2 refined the supported G1 region without using entry or economics.

Development selected:
- LONG;
- reference start 01:00 UTC (08:00 WIB);
- reference duration 150m;
- execution horizon 720m;
- 210 signals;
- continuation 89.5%;
- resolved same-side 90.8%;
- Wilson LB 84.6%;
- 5/5 supportive local neighbors;
- 4/4 positive Development blocks.

Historical replication:
- External: 97 signals, 81.4% continuation, 84.0% resolved, Wilson 72.6% — PASS.
- Reference Validation: 89 signals, 89.9% continuation, 89.9% resolved, Wilson 81.9% — PASS.

The winner remained on the maximum execution-horizon boundary (720m), so exact execution coordinates are not localized.

## Post-run descriptive timing anatomy
The selected-session audit shows that the 720m execution variable is conflating two distinct clocks: waiting for the first valid pressure signal and allowing the signal to resolve.

Signal delay from execution start:
- Development median 90m; 90th percentile ~300m.
- External median 50m; 90th percentile ~247m.
- Reference Validation median 60m; 90th percentile ~324m.

For sessions that achieved same-side continuation, signal-to-target delay was much shorter:
- Development median 25m; 90th percentile ~176.5m.
- External median 20m; 90th percentile ~162m.
- Reference Validation median 15m; 90th percentile ~116m.

This means the 720m boundary does **not** imply that ETH requires 720 minutes of post-entry patience. Most same-side resolutions occur far sooner after the signal; the long horizon mainly admits later-arriving signals.

## Scientific consequence
Do not extend a single monolithic execution window again. The next experiment must decompose:
1. **setup acquisition window** after the reference ends; and
2. **post-signal follow-through horizon** after the setup is causally known.

Only after those clocks are independently localized should downstream structure/entry discovery proceed.

Previous ETH Z2/Z3 rules and Z5 L06 entry remain historical comparators only.

Research/shadow only. No live promotion.
