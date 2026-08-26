# B27DV — B27DQ LONG + F15 SHORT20 Phantom-Free Live Control Plane — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Build and audit a shadow-first live control plane for the already-frozen BTC strategies without changing trading logic:
- LONG: exact B27DQ four-zone F85 portfolio and live-executable N+2 runner timing.
- SHORT: exact B27DS/B27DU 20:00 UTC F15 SAME_BAR_REJECTION strategy.

B27DV is engineering/live-readiness work. It does not search parameters, change clocks, add filters, or authorize real-money execution.

## Frozen strategy rules
No change is permitted to B27DQ LONG zones, F85 entry geometry, same-bar confirmation, next-5m-open entry, runner policy, F35/E10/E20 logic, fee/notional, or one-BTC-position semantics.

No change is permitted to SHORT20 reference start 20:00 UTC, 5h30 reference duration, 01:30-08:00 UTC execution, Low K1 OPP0, causal leave, F15 same-bar close below F15, next-5m-open entry, F65 completed-close invalidation, E20_DOWN target, fee/notional, or time exit.

## Control-plane requirements
The new shadow engine must be separate from the legacy EMA/MTF `bbc_live.py` path and default to no exchange writes.

1. **Closed-5m event gate**
   - decisions are accepted only on 5-minute aligned completed-bar timestamps;
   - duplicate completed-bar events are idempotent;
   - out-of-order completed bars fail closed;
   - an entry intent can only appear at the confirmation-bar close / next-bar-open boundary, never before it.

2. **Durable state / restart**
   Persist at minimum: last processed closed bar, lifecycle state, candidate/trade identity, side/source, entry/exit metadata, runner armed flag, active floor, pending floor/order identifiers and acknowledgement state.
   Re-instantiating the engine from the same store must restore the exact state.

3. **Authoritative BTC lock**
   A transactional shared-store lease must permit at most one BTC position owner. Two engine instances sharing the store must not both acquire the slot.

4. **Entry acknowledgement**
   `submit` is not `ACTIVE`. Lifecycle must be `ENTRY_PENDING_ACK` until an exchange acknowledgement/fill is applied.

5. **Protective-floor acknowledgement**
   A newly requested floor is `PENDING_ACK` and may not become the active protective floor until acknowledgement. B27DQ N+2 timing remains the research-side causal buffer.

6. **Startup exchange reconciliation**
   - exchange open / local idle: adopt or halt safely while claiming the BTC slot;
   - local active / exchange flat: clear stale local position and release slot;
   - material side/identity mismatch: fail closed / halt, never open a second position.

7. **Portfolio replay parity**
   Rebuild frozen B27DQ raw LONG candidates plus frozen SHORT20 candidates and feed them chronologically through the control-plane arbitration. FIRST_SIGNAL_WINS tie-break remains LONG first. Accepted/blocked candidate identities must match B27DT exactly for pooled-major history.

## Frozen historical controls
B27DQ pooled-major control must reproduce approximately N=227, WR=72.2%, PF=2.25, net=+$289.76, max loss streak=3.

B27DT LONG+SHORT20 FIRST_SIGNAL_WINS control must reproduce pooled-major N=283, combined net=+$367.49, LONG N=227, SHORT N=56, displaced baseline LONG=0.

## Engineering tests / gates
B27DV control-plane support requires ALL:
- B27DQ prerequisite parity PASS;
- B27DT LONG+SHORT20 candidate/portfolio parity PASS;
- accepted candidate ID set and order 100% equal to frozen FIRST_SIGNAL_WINS result;
- duplicate closed-bar replay creates zero duplicate entries;
- out-of-order bar is rejected/fails closed;
- restart restore checks PASS at entry-pending, active-position, and floor-pending states;
- two-instance BTC-lock test proves only one acquisition;
- entry cannot become ACTIVE before ACK;
- requested floor cannot become active before ACK;
- startup reconciliation tests PASS for adopt, stale-local-clear, and mismatch-halt cases.

## Status labels
`B27DV_SHADOW_CONTROL_PLANE_SUPPORTED` only if every frozen gate above passes.
Otherwise `B27DV_SHADOW_CONTROL_PLANE_NOT_READY` with failed checks persisted.

Even a PASS means **shadow-control-plane ready**, not real-money authorization. A later experiment must connect raw live 5m market events to this engine and prove forward shadow parity before live orders are enabled.
