# ETH LONG B27Y-Adapt — F75 Post-H2 Breakout Extension Atlas — Preregistration

## Purpose
Adapt the BTC B27Y milestone to the ETH-specific F75 entry cohort selected in B27W-Adapt.

H2 remains a structural milestone, not TP.

Frozen cohort:
- ETHUSDT
- LONDON_TO_NEWYORK LONG
- K1 OPP0
- causal leave after first High-touch episode
- F75 pre-H2 entry
- exact B27W-Adapt fill and H2 identities

## Measurements
For every F75 fill:
- if H2 never occurs before structural terminal/session end, classify NO_H2;
- if H2 occurs, study raw completed 5m bars from the H2 bar through New York session end.

H = completed London High, L = completed London Low, R=H-L.

Strict breakout acceptance:
- FIRST_CLOSE_BREAK = first completed 5m bar at/after H2 with close > H.

Maximum extension:
- max_high_extension = (max(high)-H)/R
- max_close_extension = (max(close)-H)/R

Frozen extension atlas, descriptive only:
- E05, E10, E15, E20, E25, E30, E40, E50
- level price = H + E*R

For every extension report by partition:
- high reach / H2 paths
- high reach / all F75 fills
- close reach / H2 paths
- close reach / all F75 fills
- median minutes H2 -> first high reach when reached

Also report F75 fills, H2 count/rate, strict close-break rate, and extension distribution quantiles.

## Guardrails
- No target is selected in B27Y-Adapt.
- No stop, runner, clock, candle filter, EMA, ATR, volume, or regime tuning.
- No live changes.

Research only.