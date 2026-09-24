# SOL Derivatives-State Transition V4 — Verified Result

Run ID: 35955376824
Head SHA: 7f2f819790466caee2fbb5e6f3e04efd806247a2
Status: SUCCESS

Six frozen sign-based states, no threshold tuning.

Key observation:
- NEW_LONG_BUILD is extremely high coverage of ex-post long legs:
  - L2 leg-hit 81-86%, early-hit 54-59%
  - L3 leg-hit 87-90%, early-hit 58-62%
  - L5 leg-hit 87-92%, early-hit 54-61%
- ABSORPTION_RELEASE also has high leg-hit/early-hit.
- Despite that, every state×target has negative expectancy in every calendar year.
- Main diagnostic: states fire extremely often (e.g. NEW_LONG_BUILD roughly 18-40 executed trades/week depending target/year), so the state identifies broad bullish participation but not a unique ignition event. Repeated entries while the same state persists create many false/redundant attempts.

No V4 gate passed.

Interpretation:
The state information is not useless: it overlaps a large share of real long legs early. The next finite test should change event semantics, not thresholds: trade only the OFF->ON transition of a frozen state, preventing repeated re-entry while the same derivatives state remains active.

VERDICT: NO_DERIV_STATE_GATE_PASS_V4__STATE_EVENT_SEMANTICS_NEXT
