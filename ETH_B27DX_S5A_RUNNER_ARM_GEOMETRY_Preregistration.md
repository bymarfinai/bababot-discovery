# ETH B27DX — S5A Live-Executable Runner Arm Geometry — Preregistration

## Purpose
Test whether ETH's positive-but-below-BTC S4 fixed-exit portfolio can gain BTC-class economic concentration through causal dynamic management, while preserving the already-frozen ETH-native structure and trade geometry.

S5A changes **runner arm milestone only**. It does not tune entry, lifecycle, clocks, pre-arm invalidation, breathing gap, ratchet step, leverage, fee, or data partitions.

## Frozen S4 signal/portfolio layer
- side: LONG only;
- reference: **R300**;
- execution horizon: **X360**;
- entry: **F75**;
- pre-arm completed-close invalidation: **F20**;
- structural clocks: **05:00, 09:00, 10:00, 16:00 UTC**;
- exact B27DX corrected causal grammar;
- same candidate chronology and global one-position rule;
- $500 notional and $0.40 round-trip fee;
- weekdays only;
- same External / Development / Reference Validation partitions.

Frozen S4 fixed baseline for comparison:
- target **E25**;
- Pooled Major accepted N **478**;
- WR **62.8%**;
- PF **1.42**;
- expectancy **+$0.81/trade**;
- net **+$385.75**;
- frequency **1.393/wk**;
- max loss streak **5**.

## ETH runner principle
S5A transfers BTC's **causal runner grammar**, not BTC's arm coordinate.

For each arm milestone `A`:
1. Before arm, management remains the frozen completed-close F20 invalidation.
2. The first completed 5m bar whose high reaches arm milestone `A` arms the runner. No fixed TP is taken.
3. Initial breathing floor is frozen at **A - 0.10R**.
4. Ratchet ladder step is frozen at **0.10R**. For every completed-close milestone one 0.10R step above the arm, the desired floor advances by one 0.10R step and never decreases.
5. A floor learned from completed bar N is exchange-active only from the start of **bar N+2**, preserving the B27DQ placement buffer.
6. During N+1, only the previously active floor is executable. During the initial arm buffer, F20 completed-close invalidation remains available.
7. Once a floor was already active before a bar starts:
   - if open <= floor, exit at that open;
   - else if low <= floor, exit at the floor, with portfolio availability after the completed 5m bar.
8. Execution-end time exit remains at execution-end open.
9. Floor never decreases and no same-bar/newly-learned floor is credited retroactively.

## Arm grid — only changing dimension
Test only milestones already inside the S3A supported target family:

`E10, E15, E20, E25, E30, E35, E40`

No intermediate arm value may be added after results are seen.

Examples of frozen breathing floor:
- E10 arm -> E00 initial floor (H);
- E20 arm -> E10 initial floor;
- E25 arm -> E15 initial floor;
- E40 arm -> E30 initial floor.

The 0.10R breathing gap and 0.10R ratchet step are fixed in S5A and are not optimized here.

## Exact portfolio rescore
Runner exits change holding time, so every arm variant must:
- rebuild the full candidate stream;
- rerun the same chronological global one-position lock for every partition;
- use the same exact-entry tie rule as S4: latest execution-start timestamp first, then execution-clock ascending.

Do not replace PnL on the already-accepted S4 trade list.

## Execution stress
Primary score: **0 bps**.
Diagnostic stress: **5 bps** adverse execution:
- entry worsened by 5 bps;
- floor / invalidation / time exits worsened by 5 bps;
- no artificial slippage is applied to the arm event because it is not an exit.

## Arm support gate
An arm is `SUPPORTED` only if all are true at 0 bps Pooled Major:
- net > S4 fixed baseline net **+$385.75**;
- PF >= **1.80**;
- WR >= **70%**;
- expectancy > S4 fixed baseline expectancy **+$0.81/trade**;
- accepted N >= **80% of 478**;
- every major partition has net > 0 and PF > 1.0;
- no floor is scored before its N+2 activation timestamp;
- 5 bps Pooled Major PF >= 1.0 and net >= 0.

This is a demanding runner-promotion gate, but it is still below the final BTC-quality gate so arm discovery is not forced to cherry-pick the BTC benchmark.

## Arm-family topology
A native arm family requires at least **2 adjacent SUPPORTED arm milestones** on the preregistered 5-point grid.

An isolated high-performing arm is reported but is not promoted as a stable ETH-native arm family.

## Final BTC-quality diagnostic
For every arm report whether Pooled Major meets or exceeds the frozen BTC B27DX LONG benchmark:
- WR >= **71.9%**;
- PF >= **2.22**;
- expectancy >= **+$1.26/trade**;
- every major partition positive.

This is diagnostic in S5A. Final strategy acceptance still requires the chosen management family, portfolio lock, and stress validation.

## Reporting
For fixed E25 baseline and each runner arm report:
- candidates / accepted / blocked;
- accepted trades/week;
- WR, PF, expectancy, net, max loss streak;
- per-partition results;
- per-clock contribution;
- armed count;
- active-floor exits, gap-open exits, buffer F20 exits, time exits;
- scheduled floor updates / activations;
- 0 bps and 5 bps results;
- support and BTC-quality diagnostic status.

## Decision states
- `ETH_S5A_NATIVE_ARM_FAMILY_SUPPORTED`
- `ETH_S5A_SUPPORTED_ARM_ISOLATED`
- `ETH_S5A_NO_SUPPORTED_ARM`
- `ETH_S5A_CAUSAL_AUDIT_FAILED`

## Guardrails
- Arm milestone is the only tuned dimension.
- No clock pruning.
- No breathing-gap or ratchet-step sweep.
- No entry/target/stop/lifecycle tuning.
- No H/H2 selection.
- No leverage changes.
- No live BBC changes.
