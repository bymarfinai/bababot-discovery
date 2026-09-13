# SOL ORB Structure Detector v1 — Preregistration

## Goal
Build an interpretable SOLUSDT detector whose output can directly become a live entry event like the ORB example: opening range -> breakout -> retest -> acceptance -> LONG entry.

This is structure discovery, not TP/SL optimization and not an attempt to rescue prior losing candidates.

## Frozen initial habitat
- Direction: LONG only.
- Initial habitat: 23:00-00:00 UTC / 06:00-07:00 WIB, inherited only as the first investigation habitat from SOL Economic-First H23.
- Source timeframe: 5m.
- ORB: first 15 minutes = first three 5m candles.
- Development only. OOS remains closed.

## Detector states
1. BUILD_ORB: compute ORB high, low and midpoint.
2. BREAK_HIGH: first 5m close above ORB high.
3. RETEST_HIGH: within the next 30 minutes, price trades back to ORB high/inside ORB while candle close remains at or above ORB midpoint.
4. ACCEPT_HIGH: after the retest, a later 5m candle closes above ORB high.
5. LONG_ENTRY: next 5m candle open.

Negative classifications:
- NO_BREAK_HIGH
- BREAK_HIGH_NO_RETEST
- FAILED_BREAK_HIGH
- RETEST_NO_ACCEPT
- ACCEPT_HIGH_NO_NEXT_BAR

Positive classification:
- BREAK_RETEST_ACCEPT_LONG

## Anti-overfit rules
- No VWAP, EMA, Fibonacci, volume gate, regime gate, TP or SL in v1.
- No parameter sweep in v1.
- No changing the rule after inspecting individual losses.
- First output is prevalence and event-level signal inventory, not a claim of profitability.
- Economic evaluation comes only after the detector has produced an auditable structural population.

## Questions v1 must answer
- How often does the full break -> retest -> acceptance sequence occur?
- How often does breakout fail, never retest, or retest without acceptance?
- Are signals frequent enough to be a plausible trading mechanism?
- Only after that: what is the forward-return / TP-SL economics of each structure class?

## Implementation
`research/sol_orb_structure_detector_v1.py`

The script accepts an existing SOLUSDT 5m CSV and writes one row per daily habitat with timestamps for breakout, retest, acceptance and executable next-bar entry.
