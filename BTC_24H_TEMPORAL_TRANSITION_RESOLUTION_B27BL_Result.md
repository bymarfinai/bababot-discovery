# B27BL — BTC 24H Temporal Transition Resolution Audit — Result

**Audit status: PASS.** Temporal regime-state anatomy only; no classifier/refit, price threshold, LONG/SHORT mapping, entry, stop, target, fee, WR, PF, PnL, session filter, or live change was used.

B27BH identity reproduced exactly: **1,023 episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.**

At the first completed SIDEWAYS bar the conceptual state is `PENDING`. An episode resolves only when a later completed 4H bar causally returns to the origin directional state or reaches the opposite directional state.

## Pooled-OOS temporal resolution

| Age since first SIDEWAYS | Resolved | Still PENDING | P(transition \| pending) |
|---|---:|---:|---:|
| +4h | 244/555 = 44.0% | 311 = 56.0% | 56.3% |
| +8h | 403/555 = 72.6% | 152 = 27.4% | 50.7% |
| +12h | 465/555 = 83.8% | 90 = 16.2% | 43.3% |
| +16h | 492/555 = 88.6% | 63 = 11.4% | 41.3% |
| +20h | 503/555 = 90.6% | 52 = 9.4% | 38.5% |
| +24h | 509/555 = 91.7% | 46 = 8.3% | 34.8% |

## One-bar survival effect — OOS

This asks: after the first SIDEWAYS bar, if the next 4H state is **still SIDEWAYS**, how much does eventual opposite-direction transition probability rise relative to first-SIDEWAYS baseline?

| Partition | Origin | Baseline transition | Still pending N | Transition if still pending | Lift |
|---|---|---:|---:|---:|---:|
| external | BULL | 36.2% | 106 | 42.5% | +6.3pp |
| external | BEAR | 48.1% | 66 | 53.0% | +4.9pp |
| reference_validation | BULL | 52.0% | 74 | 66.2% | +14.2pp |
| reference_validation | BEAR | 59.0% | 65 | 70.8% | +11.8pp |
| POOLED_OOS | BULL | 43.8% | 180 | 52.2% | +8.5pp |
| POOLED_OOS | BEAR | 54.1% | 131 | 61.8% | +7.7pp |

## Cause-specific resolution by SIDEWAYS duration — pooled major

| SIDEWAYS duration | RESUME resolves | TRANSITION resolves | Total resolving at age |
|---|---:|---:|---:|
| 1 bar / 4h | 306 | 200 | 506 |
| 2 bar / 8h | 123 | 168 | 291 |
| 3 bar / 12h | 39 | 72 | 111 |
| 4 bar / 16h | 20 | 29 | 49 |
| 5 bar / 20h | 7 | 7 | 14 |
| 6 bar / 24h | 2 | 4 | 6 |

## Frozen promotion gate

- Exact identity / causal timing: **PASS**.
- Pooled-OOS resolved by +8h >=40%: **PASS** (72.6%).
- Both origins pooled-OOS one-bar pending transition lift >=10pp: **FAIL**.
- Positive one-bar survival effect in external AND validation for both origins: **PASS**.
- Pooled-OOS pending N after one bar >=30 per origin: **PASS**.
- Pooled-OOS resolved by +12h >=70%: **PASS** (83.8%).

**Frozen verdict: `B27BL_TEMPORAL_PENDING_STATE_NOT_SUPPORTED`.**

## Interpretation boundary

A supported result validates only the temporal `PENDING`-state concept: SIDEWAYS age itself contains causal information and many episodes resolve naturally without forcing a first-bar classification. It does not yet define the production detector state machine or any trading behavior.

Research only. Live BBC unchanged.
