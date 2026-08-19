# BTC Friday Pre-entry Fingerprint P0 — Preregistration

**Research-only. Live BBC untouched. Frozen before result.**

## Question
Does the exact entry-time candle relationship already identified in Friday F6.38/F6.39 carry a high win rate when applied prospectively at entry to **all** BTC Friday opportunities, without using any post-entry branch information?

## Canonical Friday opportunity
- BTCUSDT
- every Friday 08:00 UTC
- LONG
- entry at 08:00 UTC 5m open
- TP +2.00%
- SL -0.70%
- max hold 360 minutes
- $500 notional
- 0.15% round-trip fee
- adverse-first on same 5m TP/SL ambiguity
- historical anchor follows `research/f517_regime_attribution.py`

## Pure pre-entry fingerprint
At entry time `T`, use only completed 5m bars in `[T-20m, T)`.

Reuse the exact F6.38/F6.39 relationship with no threshold change:

`BALANCE = last_preentry_upper_wick_ratio > (last_preentry_body_ratio - median(body_ratio of prior 3 completed 5m bars))`

All geometry is normalized by each candle's high-low range exactly as in F6.37.

No WATCH/F6.29/F6.31/post-entry information is permitted.

## Evaluation
Historical sample is the canonical F5.17 period: 2023-12-02 through 2026-07-30 exclusive, 138 Friday opportunities expected.
- Discovery chronology: first 82 Fridays (existing canonical split)
- Validation chronology: remaining 56 Fridays
- Full historical: all 138

Post-cutoff diagnostic/OOS rows, if available from the existing extended Friday loader, are reported separately and never used to alter the rule.

For BALANCE=True and BALANCE=False report N, wins, WR, PnL, expectancy, PF, and four chronological blocks.

## 80% target
This is an identification target, not a guarantee of future wins.
A pure pre-entry fingerprint qualifies as `BTC_FRIDAY_80_CANDIDATE` only if:
1. BALANCE=True full historical N >= 20;
2. full historical observed WR >= 80%;
3. discovery N >= 10 and WR >= 75%;
4. validation N >= 8 and WR >= 75%;
5. validation expectancy > 0 and PF > 1;
6. at least 3/4 chronological BALANCE=True blocks have positive PnL.

If any gate fails: `REJECT_AS_80_CANDLE_IDENTIFIER`.

## Guardrail
No threshold sweep, inverse rule, alternate wick/body formula, lookback change, time shift, TP/SL change, or feature combination may be introduced after viewing P0. If P0 fails, a separately preregistered morphology-discovery phase may follow.