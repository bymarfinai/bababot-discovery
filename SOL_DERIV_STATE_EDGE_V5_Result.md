# SOL Derivatives-State Rising Edge V5 — Verified Result

Run ID: 35955636686
Head SHA: 84a9224ecb44210aa9327c251aea6ee99d2b7c86
Status: SUCCESS

V5 changed only event semantics from state-active to OFF->ON rising-edge. No thresholds or state definitions changed.

Result:
- All calendar metrics are exactly identical to V4.
- Artifact-level verification: V4 and V5 Selected/Trades files contain exactly 47,626 rows each and the complete target/state/partition/entry/exit/outcome sequences are byte-equivalent after parsing.
- Therefore repeated entry while one continuous state remained ON was NOT the cause of V4 losses.
- In practice, state episodes turn OFF and ON again before the prior trade completes, so one-position semantics already collapses persistent-state repeats. The remaining issue is many distinct false ignition episodes.

Conclusion:
Broad 15m derivatives states (OI/funding/top-vs-global/taker) are useful as context because they overlap a high fraction of real long legs, but they are not precise enough to serve as entry triggers. The next information layer must be finer-grained ignition evidence (true trade-level/1m order-flow, CVD/flow acceleration, spot-vs-futures divergence, and/or genuine order-book/liquidation data where historical coverage exists).

VERDICT: NO_RISING_EDGE_GATE_PASS_V5__FALSE_IGNITION_EPISODES
