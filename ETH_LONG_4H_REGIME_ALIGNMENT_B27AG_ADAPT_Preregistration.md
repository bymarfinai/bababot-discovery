# ETH LONG B27AG-Adapt — 4H HH/HL Regime Alignment Audit — Preregistration

## Purpose
Adapt the BTC B27AG attribution milestone to the frozen ETH LONG pipeline only. This is an attribution audit, not a new entry filter or promotion gate.

## Frozen ETH local setup
- ETHUSDT perpetual
- LONDON_TO_NEWYORK / LONG / K1 / OPP0 from B27Q-Adapt
- F75 structural fills from B27W-Adapt
- post-H2 E10 reach identity from B27Y-Adapt
- EARLY_RECLAIM fixed E10+D60/F15 economics from B27AA-Adapt
- EARLY_RECLAIM E10 profit-lock hybrid economics from B27AC-Adapt
- no entry, F75, E10, F15, runner, fee, session, or timeframe retuning

## Frozen 4H regime detector
Reproduce the repository pre-existing `v4h_regime_endpoint.py` SwingRegime defaults exactly:
- UTC 4H bars assembled only from complete raw 5m bars
- EMA fast 7, slow 20
- ATR period 14 with repository recurrence
- swing lookback 5
- swing ATR separation 0.5
- swing candidate centered at i-2 and only known when 4H bar i completes
- BULL iff hh>=2, hl>=2, EMA7>EMA20, completed close>EMA20
- BEAR iff lh>=2, ll>=2, EMA7<EMA20, completed close<EMA20
- otherwise SIDEWAYS

State attached to a local signal is the latest completed 4H state whose availability timestamp bar_start+4h <= K1 signal_ts. No incomplete 4H information may be used.

## Frozen outputs
By partition and pooled-major, report:
1. K1 opportunity count and target-break probability by regime.
2. F75 fill count and H2 rate by regime.
3. E10 reach rate conditional on H2 by regime.
4. EARLY_RECLAIM fixed and B27AC hybrid N/WR/PF/expectancy/net by signal-time regime.

## Directional-support readout
ETH LONG regime alignment is directionally supported only if pooled-major:
1. F75 H2 rate in BULL > BEAR;
2. E10 reach given H2 in BULL > BEAR;
3. EARLY_RECLAIM fixed-E10 expectancy in BULL > BEAR.

This readout does not authorize dropping BEAR or SIDEWAYS trades. Any regime-gated strategy requires a separate preregistered milestone.

Research only; no live changes.