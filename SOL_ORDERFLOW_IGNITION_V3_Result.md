# SOL Order-Flow / Liquidity Ignition V3 — Verified Result

Run ID: 35954747713
Head SHA: 42e8903501099ecd0770eb533351fd0e9ee4c314
Status: SUCCESS

Data:
- 5m price coverage 99.76977%
- Data Vision 15m flow rows 128,640
- derivatives metrics rows 384,276
- funding rows 4,092
- 24 independent flow/derivatives fields retained at >=90% coverage
- liquidationSnapshot historical probe: 0/8 usable (all representative dates 404), therefore not used

Frozen transfer highlights:
- L2 FLOW_ONLY: 2024 WR 37.22%, 7.45/wk, exp -0.034%; 2025 31.72%, 4.28/wk, exp -0.195%; 2026 27.50%, 1.14/wk, exp -0.217%.
- L3 FLOW_ONLY: 2024 WR 29.15%, 7.96/wk, exp +0.016%; 2025 23.92%, 4.81/wk, exp -0.193%; 2026 21.95%, 2.34/wk, exp -0.186%.
- L5 FLOW_ONLY: 2024 WR 18.50%, 3.26/wk, exp -0.040%; 2025 20.69%, 1.09/wk, exp +0.091%; 2026 11.11%, 0.26/wk, exp -0.483%.
- PRICE_PLUS_FLOW did not produce robust improvement.

Important FLOW_ONLY feature importance:
- L2: OI change 60m, OI change 4h, top-vs-global positioning, top-account change, funding z, top-account level, 60m taker imbalance.
- L3: top-vs-global positioning, funding z, top-account level, OI change 60m, funding change/rate, OI change 4h.
- L5: top-account level, funding z, top-vs-global positioning, funding rate/change, OI change 4h/60m.

Interpretation:
Independent derivatives state contains some development-period signal but it is not stable across 2025/2026. Instantaneous taker flow is not the dominant information. The next finite hypothesis family should test regime-normalized derivatives state transitions: new-long build, short-squeeze, absorption, and deleveraging reversal.

VERDICT: NO_ROBUST_ORDERFLOW_IGNITION_V3
