# B27DX — F85 LONG Future-Ambiguous-Terminal Causality Correction — Preregistration

**Status:** PREREGISTERED before result-bearing rescore.

## Trigger
B27DW raw event replay found exactly one extra causal LONG candidate versus the frozen B27DQ/B27DE lineage: `reference_validation|LONG|RAW_0530|2025-09-11 12:30:00+00:00`.

The raw live-safe adapter had already observed, in order, frozen range -> High K1 -> causal leave -> first pre-H2 F85 touch -> same-bar close above F85 -> next-bar open. The historical B27DE case nevertheless returned `AMBIGUOUS_H2_VS_OPPOSITE_BREAK` because a **later** terminal bar simultaneously touched H and closed below L, and B27DE discarded the whole session before evaluating an earlier F85 entry.

That discard is future-dependent and cannot be reproduced live without look-ahead.

## Frozen correction
Do **not** suppress a causally completed F85 signal because of a terminal event that occurs after the entry boundary.

No other rule changes:
- same four B27DQ zones;
- same reference/execution clocks;
- same K1 OPP0, causal leave, first-F85-touch semantics, same-bar confirmation and next-open entry geometry;
- same ALT touch-first-half and RAW range-completed-second-half filters;
- same B27DQ N+2 live runner management;
- same one-BTC-position lock;
- same SHORT20 strategy.

## Rescore method
1. Rebuild raw event signals from B27DW and assert the historical lineage has **0 missing causal LONG candidates and exactly 1 extra** caused by the future-ambiguous-terminal branch.
2. Construct the extra candidate using only data known by its 12:30 UTC entry, then simulate the already-frozen fixed F35/E20 path causally for bookkeeping.
3. Append that candidate to the prior four-zone stream and apply the unchanged B27DQ live-executable runner.
4. Re-run the global one-BTC-position lock by partition.
5. Re-run B27DQ 0/2/5/10 bps stop-slippage sensitivity.
6. Merge corrected LONG with frozen SHORT20 and re-run FIRST_SIGNAL_WINS.

## Gates
Support requires:
- exactly one identified future-dependent omission and no canonical candidate lost by raw replay;
- corrected LONG candidate universe contains prior 244 plus exactly one causal candidate;
- no rule/clock/filter alteration beyond deleting the future-dependent session veto;
- corrected B27DQ pooled-major remains WR >=70%, PF >=2.0, net >$250 and max loss streak <=4;
- 5 bps stop-slippage remains PF >1.8 and net >$200;
- corrected LONG+SHORT20 combined portfolio remains positive incremental versus corrected LONG-only;
- all outputs and the extra trade's actual acceptance/blocking/outcome are persisted.

Status: `B27DX_CAUSAL_LONG_CORRECTION_SUPPORTED` only if all gates pass; otherwise `B27DX_CAUSAL_LONG_CORRECTION_NOT_SUPPORTED`.

Research/shadow engineering only. No exchange writes and legacy live BBC remains unchanged.
