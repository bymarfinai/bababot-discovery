# B27DO — 4-Zone Hybrid Exit — Preregistration

## Purpose
Test the exact user-selected hybrid exit policy on the frozen B27DK 4-zone F85 LONG candidate stream, using B27DN's already-frozen E10 breathing mechanics without changing any entry logic or thresholds.

## Frozen zone policy
- ALT_0330: **FIXED_E20** baseline exit.
- RAW_0530: **E20_TOUCH_E10_BREATHING_STEP10_RUNNER** from B27DN.
- LONDON 08:00: **E20_TOUCH_E10_BREATHING_STEP10_RUNNER** from B27DN.
- RAW_2330: **E20_TOUCH_E10_BREATHING_STEP10_RUNNER** from B27DN.

## Frozen mechanics
For the three runner zones, reuse B27DN exactly:
1. First E20 high-touch arms the runner instead of taking fixed E20.
2. Starting the next 5m bar, initial hard floor = E10 = H + 0.10R.
3. Completed-close E30 -> E20 floor; E40 -> E30; E50 -> E40; and so on in 0.10R steps.
4. Floor never decreases.
5. Gap/open and intrabar floor handling, F35 pre-arm invalidation, time exit, fee, notional and execution assumptions are unchanged from B27DN.

ALT_0330 remains exactly the B27DK fixed-E20 baseline, including immediate E20 high-touch TP.

## Exact portfolio rescore
The hybrid exit durations can change overlap. Therefore B27DO must rebuild the complete 242-candidate stream chronologically and rerun the same one-BTC-position global lock for every partition. It is invalid to add per-zone net PnL values directly.

## Frozen comparison
Report:
- Fixed E20 baseline
- Universal B27DN E10 breathing runner
- B27DO hybrid
for every partition and pooled-major, plus pooled-major per-zone contribution under the hybrid lock.

## Decision label
`B27DO_HYBRID_PROMISING_EXPLORATORY` only if pooled-major hybrid:
- total net PnL > fixed-E20 baseline;
- total net PnL > universal B27DN;
- WR > universal B27DN WR;
- PF >= 1.80;
- accepted N >= 80% of fixed baseline accepted N;
- every major partition remains net positive.
Otherwise `B27DO_HYBRID_NOT_PROMISING`.

## Evidence status
Exploratory optimization. The hybrid choice was selected after inspecting earlier per-zone B27DN results, so it is not pristine OOS confirmation.

Research/operating exit experiment only. Live BBC remains unchanged.