# ETH London -> New York M4 Structure Ladder — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Recalibrate the London->New York continuation structure without treating H2 as a take-profit or final success state.

The exact causal ladder under test is:

`K1 pressure -> causal leave -> pre-H2 retracement fill -> H2 arrival -> strict breakout close > H -> post-confirmation E10/E20 extension`

M4 is structural calibration only. No stop, PnL, fee, slippage, runner, leverage, portfolio lock, or trading-WR selection is allowed.

## Frozen cohorts
Primary: ETHUSDT perpetual using exact persisted M2 filled entries at F95/F90/F85/F80/F75.
Control: BTCUSDT using exact persisted B27W filled entries at the same five fractions.

Frozen sessions remain:
- London reference 08:00-13:30 UTC.
- New York active session 13:30-20:00 UTC.
- LONG K1 OPP0 only.
- Raw 5m chronology.
- Historical partitions: external, development, reference_validation, August telemetry.

## Frozen event definitions
- `H` and `L` are the completed London High/Low and remain immutable.
- Entry identities/timestamps are reused unchanged from ETH M2 / BTC B27W.
- `H2 arrival` is the first post-leave arrival bar with `high >= H`; it is a structural touch only.
- `strict breakout` is the first completed post-entry raw 5m candle with `close > H`, provided no earlier completed post-entry candle closed `< L`.
- `opposite failure` is the first completed post-entry candle with `close < L` before strict breakout.
- If H2 bar itself closes `> H`, classify `H2_IMMEDIATE_BREAKOUT`.
- If H2 bar closes `<= H`, classify `H2_REJECTION`; a later strict breakout may still occur.
- `E10 = H + 0.10R`, `E20 = H + 0.20R` where `R=H-L`.
- To preserve causal stage order, E10/E20 extension scoring begins only from the **next raw 5m bar after the strict-breakout bar completes**. Same-breakout-bar overshoot is reported separately as telemetry and cannot count as causal post-breakout extension.
- All stage scoring ends at 20:00 UTC. No post-session event is used.

## Required outputs per asset / partition / entry level
- filled entries N;
- H2 arrival count/rate from fill;
- strict breakout count/rate from fill;
- strict breakout rate conditional on H2;
- H2 immediate-breakout count/rate;
- H2 rejection count;
- later strict-breakout rate conditional on H2 rejection;
- opposite failure before strict breakout;
- no strict breakout by session end;
- causal E10 extension rate conditional on confirmed strict breakout;
- causal E20 extension rate conditional on confirmed strict breakout;
- same-breakout-bar E10/E20 overshoot telemetry;
- median fill->H2 minutes;
- median H2->strict-breakout minutes;
- median strict-breakout->E10/E20 minutes.

## Interpretation rule
M4 does not choose an entry level and has no economic promotion gate.

The purpose is to identify which structural stage actually carries the continuation edge:
- H2 arrival only,
- confirmed breakout,
- or confirmed breakout followed by extension.

ETH may be compared descriptively with BTC control, but BTC coordinates may not be imposed on ETH based on this run.

## Mandatory assertions
1. ETH M2 and BTC B27W filled entry identities/timestamps are reused unchanged.
2. Every entry is strictly before H2 when H2 exists.
3. Strict breakout requires completed `close > H`; wick-only H2 never counts as breakout.
4. Opposite failure requires completed `close < L` before breakout.
5. H2 immediate breakout means exact same raw 5m bar as first H2 arrival and strict breakout.
6. Causal E10/E20 stage scoring starts only after breakout-bar completion.
7. No event after 20:00 UTC is scored.
8. Raw 5m coverage for ETH and BTC must each be >=99.5%.

Research only. Live BBC unchanged.