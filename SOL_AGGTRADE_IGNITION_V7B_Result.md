# SOL High-Resolution AggTrade Ignition V7B — Verified Result

Run ID: 35961007070
Head SHA: 1f3141164f0178342b72d014abe8ec30451f26cc
Status: SUCCESS
Artifact ID: 10792726210

Data / coverage:
- 19,849 frozen NEW_LONG_BUILD rising-edge parent events across 2023-2024.
- 2023 aggTrade event coverage: 100.00%.
- 2024 aggTrade event coverage: 100.00%.

Execution:
- TP +2%, SL -2%, RR 1:1, 0.15% round-trip cost, one active position.

2024 parent baseline:
- N 1,347
- WR 47.74%
- 25.42 trades/week
- expectancy -0.192%/trade
- mean weekly net -4.88%

Best preregistered V7B config:
- RF, 92.5th percentile score threshold
- N 479
- WR 48.85%
- 9.04 trades/week
- expectancy -0.149%/trade
- mean weekly net -1.35%
- median weekly net -2.15%

Forensics:
- zero stable differentiators under same-sign SMD >=0.10 in both 2023 and 2024.
- strongest consistent min-abs SMD was only ~0.038 (1m trade count).
- RF importance concentrated on 5m/15m trade count and total/sell/buy quote intensity rather than signed-flow direction.
- TREE mostly used 5m count, 15m count, and 15m top-5% trade concentration.

Interpretation:
Futures compressed trade sequencing contains essentially no stable winner-vs-loser separation for this parent event and TP2/SL2 target at the required daily frequency. V7B does not authorize raw-trade/OOS confirmation.

Next independent information set allowed by the V7 umbrella preregistration: spot-vs-futures trade-flow divergence/corroboration.

VERDICT: NO_V7B_PROMOTION_GATE