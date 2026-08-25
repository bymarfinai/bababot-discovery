# B27DQ — B27DO Live-Executable TP/Runner Rescore — Preregistration

## Purpose
Repair the B27DO TP/runner execution model identified by B27DP without changing the F85 entry signal, four-zone operating policy, or 03:30 fixed-E20 decision.

This is an execution-model correction, not a parameter optimization sweep.

## Frozen portfolio
- ALT_0330: fixed E20, unchanged from B27DO.
- RAW_0530: E20 touch -> E10 breathing runner.
- LONDON: E20 touch -> E10 breathing runner.
- RAW_2330: E20 touch -> E10 breathing runner.
- Same candidate stream, F35 rule, execution horizon, fee, research sizing, partitions, and global one-position chronological lock as B27DO.

## Frozen live-executable floor timing
The B27DP audit showed that a floor learned from completed bar N cannot be assumed to have been resting at the exact N+1 open.

B27DQ therefore uses a deliberate one-full-5m-bar placement buffer:

1. A new floor is computed only from completed 5m information on bar N.
2. That floor is scheduled to become exchange-active only from the start of bar N+2.
3. During bar N+1, the previously active floor remains the only stop floor.
4. For the initial ARM, there is no runner floor during the placement-buffer bar; the pre-existing completed-close F35 invalidation remains available during that buffer.
5. Multiple scheduled ratchets may exist; when their effective timestamp arrives, the active floor becomes the maximum due floor. Floor never decreases.
6. Once a floor was already active before a bar starts:
   - if bar open <= active floor, exit at bar open (`LIVE_FLOOR_GAP_OPEN`);
   - else if bar low <= active floor, exit at active floor (`LIVE_FLOOR_TOUCH`).
7. Because the stop is deliberately active before the bar being scored, B27DQ does not credit a newly learned floor inside the same/next immediate bar.
8. Execution-end exit remains at execution-end bar open if no prior exit occurs.

## Frozen ratchet structure
Same structural ladder as B27DN/B27DO:
- initial floor E10;
- completed close >= E30 schedules E20;
- close >= E40 schedules E30;
- close >= E50 schedules E40;
- etc., one 0.10R step behind.

No E10/E20/step-size sweep is allowed in B27DQ.

## Fill sensitivity (diagnostic, not optimization)
Primary score uses the causal OHLC stop model above.
Additionally report adverse stop-market fill sensitivity at 2, 5, and 10 bps on floor-trigger exits only. These are stress diagnostics; they do not change the frozen primary strategy.

## Required audits
- Reproduce fixed-E20 B27DK/B27DO parity before interpretation.
- Reproduce B27DO saved hybrid metrics before live-executable rescore.
- Global one-position chronological re-lock for every partition.
- Report candidate/accepted/blocked, wins, WR, PF, expectancy, total net, max loss streak, per-zone contribution, and exit reasons.
- Report number of floor updates, delayed activations, buffer-bar F35 exits, and gap-open exits.

## Frozen decision gate
`B27DQ_LIVE_EXECUTABLE_SUPPORTED` only if pooled-major primary live-executable hybrid satisfies all of:
- total net > fixed-E20 B27DK baseline total net;
- PF >= 1.80;
- WR >= 70%;
- accepted N >= 80% of fixed-E20 accepted N;
- every major partition total net > 0;
- no floor is scored before its frozen N+2 activation timestamp.

Otherwise `B27DQ_LIVE_EXECUTABLE_NOT_SUPPORTED`.

## Evidence label
B27DQ remains exploratory/engineering validation because the hybrid exit selection and E10 breathing concept were developed on previously inspected historical data. It is not pristine unseen OOS confirmation.

## Live deployment
Research only. Do not modify live BBC code or configuration in B27DQ.
