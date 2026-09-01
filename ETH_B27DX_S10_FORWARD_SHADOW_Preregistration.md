# ETH B27DX — S10 Pristine Forward Shadow — Preregistration

## Purpose
Freeze the two strongest non-promoted ETH B27DX hypotheses before any new forward outcomes are inspected.

S10 is not a historical optimization stage. It is the next evidence stage after S9 research freeze.

## Forward evidence boundary
- Forward scoring begins **2026-09-02 00:00 UTC**.
- No bar before that timestamp may count toward S10 forward evidence.
- Historical data may be used only to reconstruct frozen reference/event state required for causal operation; historical outcomes may not alter the frozen filters or gates.

## Frozen shared architecture
- Symbol: ETHUSDT.
- Side: LONG.
- Raw execution/event clock: 5m completed bars.
- Reference duration: R300.
- Execution horizon: X360.
- Entry: F75.
- Target: E25.
- Completed-close invalidation: F20.
- B27DX causal grammar unchanged: frozen H/L, K1 OPP0, completed leave, first legal post-leave chronology, terminal precedence/ambiguity handling, no future veto.
- One ETH position maximum; later candidates are skipped while a prior accepted ETH position remains open.
- Existing research notional/fee model remains frozen.

## Candidate A — BROAD_SHADOW_09_BEARISH_LEAVE
- Execution start: 09:00 UTC.
- Require the completed causal leave bar to be bearish: `leave_close < leave_open`.
- No body-size or wick threshold.

Historical generation evidence only, not forward proof:
- Development N70;
- retention 78.7%;
- WR 71.4%;
- PF 2.10;
- expectancy +$1.34/trade.

## Candidate B — SPARSE_SHADOW_10_BEARISH_K1
- Execution start: 10:00 UTC.
- Require the completed first K1 H-touch bar to be bearish: `k1_close < k1_open`.
- No body-size or wick threshold.

Historical generation evidence only, not forward proof:
- Development N35;
- retention 36.1%;
- WR 77.1%;
- PF 2.56;
- expectancy +$1.64/trade.

## Conflict rule
If both frozen candidates generate legally executable entries while no ETH position is open:
1. earliest causal entry timestamp wins;
2. if entry timestamps are exactly equal, BROAD_SHADOW_09_BEARISH_LEAVE has deterministic tie priority;
3. the losing simultaneous/overlapping candidate is logged as blocked, not converted into a later entry.

No candidate may use knowledge of the other candidate's future outcome.

## Forward reporting
Report each candidate independently and the globally locked two-candidate portfolio:
- candidate count;
- accepted / blocked;
- trades per week;
- wins / losses;
- WR;
- PF;
- expectancy;
- net PnL;
- max loss streak;
- 0 bps primary and 5 bps stress.

## Evidence checkpoints
Do not stop early because results look good or bad. Interpret only at predeclared accepted-trade checkpoints:
- Checkpoint 1: portfolio accepted N >= 20;
- Checkpoint 2: portfolio accepted N >= 40;
- Checkpoint 3: portfolio accepted N >= 60.

Before N20, report telemetry only and do not promote/reject.

## Forward support gate
At a checkpoint, a candidate/portfolio is `FORWARD_SUPPORTED` only if:
- WR >= 70%;
- PF >= 1.50;
- expectancy > 0;
- net > 0;
- 5 bps PF >= 1.10;
- 5 bps net > 0.

## BTC-quality forward diagnostic
Separately label BTC-quality only if:
- WR >= 71.9%;
- PF >= 2.22;
- expectancy >= +$1.26/trade;
- 5 bps PF >= 1.20 and net > 0.

The BTC benchmark is diagnostic and does not change the frozen forward support gate.

## Prohibited changes before a checkpoint
- no changing 09:00/10:00 clocks;
- no changing R300/X360;
- no F75/E25/F20 change;
- no adding/removing candle conditions;
- no wick/body threshold;
- no volatility/direction conjunction;
- no runner;
- no leverage optimization;
- no checkpoint relocation after seeing outcomes.

## Live deployment
S10 is shadow research only. Do not modify live BBC execution from this preregistration.

## Initial status
**ETH_S10_FORWARD_SHADOW_FROZEN_AWAITING_PRISTINE_EVIDENCE**