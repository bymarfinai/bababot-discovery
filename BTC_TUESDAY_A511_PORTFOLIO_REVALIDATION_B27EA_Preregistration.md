# B27EA — Tuesday A5.11 Independent Portfolio Revalidation — Preregistration

## Purpose
Test whether the already-frozen Tuesday 06:00 WIB SELL A5.11 engine can act as a **third, mechanically independent portfolio edge** beside B27DQ F85 LONG and validated SHORT20 F15.

This is not a new Tuesday optimization. A5.11 parameters, direction, clock and management are frozen exactly as documented in `BTC_Temporal_Tuesday06_Frozen_Champion.md` and `BTC_Temporal_A510_A511_RunnerRecovery_Checkpoint.md`.

Research/shadow only. No live exchange writes.

## Frozen A5.11 strategy
- BTCUSDT.
- Every Tuesday 06:00 WIB (Monday 23:00 UTC): SELL.
- Entry: actual raw 5m open at the frozen clock.
- TP 1.35%, SL 0.80%, max hold 6h.
- $500 reference notional; 0.15% round-trip fee.
- A5.2 price-path protection unchanged.
- A5.9 EMA20 FastMR unchanged.
- A5.11 EMA7 runner-recovery rule unchanged.
- Only completed 5m bars may drive management decisions.

## Required historical parity
Before interpreting B27EA, historical 2023-12-02 through 2026-07-30 must reproduce exactly within numeric tolerance:
- N=139;
- wins=89;
- WR=64.03%;
- A5.11 net=+$130.33;
- PF≈1.692;
- A5.2 actions=7;
- FastMR actions=12;
- A5.11 recoveries=4.

If parity fails, B27EA fails.

## Chronological stability gate
Use the same 139 trades ordered by entry and split into eight contiguous near-equal blocks.

Supported iff:
- >=6/8 blocks have positive net;
- first 83-trade discovery segment net >0;
- final 56-trade validation segment net >0;
- no post-result block exclusion.

Expected historical checkpoint is 7/8 positive, but B27EA recomputes it from raw 5m implementation.

## Execution/slippage stress
Reconstruct each A5.11 realized exit price from its frozen A5.11 PnL and entry price. Apply adverse slippage to both fills for a SHORT:
- entry = entry*(1-bps/10000);
- exit = exit*(1+bps/10000).

Frozen stress lanes: 0/2/5/10 bps per fill.

5bps gate:
- WR >=55%;
- PF >=1.20;
- net >0.

No TP/SL/management retuning is allowed if this fails.

## Current portfolio control
Reproduce the current **pre-B27DX** control exactly from raw candidate streams:
- B27DQ LONG + validated SHORT20;
- chronological one-BTC-position lock;
- pooled-major N=283;
- WR≈73.1%;
- PF≈2.34;
- net≈+$367.49.

B27DX remains separately reserved to correct the known one-LONG historical phantom. B27EA therefore reports compatibility against the current pre-correction control and must be rerun after B27DX before any production use.

## A5.11 candidate timestamps / lock
For each historical A5.11 trade, persist:
- entry timestamp;
- frozen side SHORT;
- exact causal A5.11 exit timestamp from the frozen management state machine;
- realized A5.11 PnL.

Merge those candidates with the current raw B27DQ + SHORT20 candidate streams and use the same deterministic `FIRST_SIGNAL_WINS` one-BTC lock. No incumbent signal is manually protected.

## Portfolio promotion gate
A5.11 is a B27EA historical portfolio candidate only if all are true:
1. historical parity PASS;
2. chronological stability PASS;
3. 5bps standalone execution stress PASS;
4. combined accepted N >283;
5. combined net > current control net;
6. combined WR >=70%;
7. combined PF >=1.80;
8. displaced current accepted trades <= floor(2%*283)=5;
9. accepted incremental A5.11 trades have positive aggregate net.

## Interpretation boundary
Even a PASS is reused historical evidence, not pristine future confirmation. Current Tuesday forward-shadow status has not yet accumulated sufficient pristine observations. A B27EA PASS would justify keeping A5.11 as the leading **third-edge candidate** and completing forward/raw-live parity, not immediate production trading.

No Tuesday parameter, weekday, direction, TP, SL, hold, EMA threshold, runner-recovery threshold, or portfolio gate may be changed after viewing B27EA results inside this experiment.
