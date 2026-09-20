# BNB B38-S21 — Preregistration Addendum (before execution)

Clarification of live-policy scoring:

- **NEXT5_RECLAIM** has a natural fixed decision horizon and will receive a causal counterfactual policy score:
  - wait through the next completed 5m bar;
  - if it closes at/above reclaim_close, restore frozen baseline management;
  - otherwise exit at that next 5m close.

- **NEXT15_RECLAIM** has a natural fixed decision horizon and will receive the analogous 15m policy score.

- **RECLAIM_HOLD**, **RECLAIM_FAILURE_HIGH_BREAK**, and **RECLAIM_BREAK_LEVEL** are discovery-only separator states in S21.
  They do not have a preregistered finite failure deadline. Assigning one after seeing results would be tuning.
  Therefore S21 reports their causal coverage/leakage/timing only. If one is robust, any executable live policy must be preregistered in a later stage.

This addendum is committed before S21 execution and before any S21 outcomes are observed.
