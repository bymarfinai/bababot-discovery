# B27BC — BTC London→NY SHORT Post-Retest#2 Equal-Distance Hard-Stop Economics — Preregistration

## Question
Does the apparent weakness of F05/F10 in B27BA come from forcing every entry to use the same absolute F65 invalidation, rather than from the entry zones themselves?

## Frozen lineage
- BTCUSDT 5m source and coverage assertions remain unchanged.
- Same B27AY/B27AZ post-Retest#2 chronology and clean windows.
- Candidate entries are frozen to **F05, F10, F15 only**.
- Fills must occur after valid Low Retest #2 plus causal leave and before the next Low revisit/direct breakdown/opposite break, exactly as B27AZ.
- E20_DOWN = L - 0.20R remains the activation milestone.
- Once E20 is activated, the exact full-position hybrid continuation logic is retained: 100% position remains open, E20 becomes the short profit ceiling from the next causal 5m bar, confirmed strict 3-bar pivot highs below the current ceiling may ratchet the ceiling downward, ceiling never rises, and session-end exit is the exact 20:00 UTC open.
- Notional = $500; round-trip fee = $0.40.

## Only variable under test
For each entry zone, test the same **distance from that entry**, in previous-London-range units:
- D30 = entry + 0.30R
- D40 = entry + 0.40R
- D50 = entry + 0.50R

Grid is therefore exactly 9 candidates: F05/F10/F15 × D30/D40/D50. No intermediate fractions or distances may be added after results are seen.

## Stop semantics
The B27BB MAE audit was wick-based, so B27BC uses a **resting hard stop**, not a completed-close invalidation.
- The hard stop is active from the fill bar onward until E20 activation.
- If a bar opens at/above the stop, exit at the actual open.
- Otherwise, if the bar high touches/exceeds the stop, exit at the exact stop.
- Because 5m OHLC cannot resolve intrabar order, if the same bar contains both a hard-stop touch and an E20 touch, **stop-first** is used conservatively.
- The fill bar is also conservative: if its high reaches the stop, the trade is counted stopped even though OHLC cannot prove whether the high occurred before or after the limit fill.
- After E20 activation, the pre-activation hard stop is disabled; the existing E20 hybrid profit-ceiling logic governs the remaining full position starting from the next causal bar.

## Mandatory audit assertions before interpretation
1. 698,112 5m rows and 100% source coverage.
2. B27AZ clean-window identities reproduce.
3. Pooled-major fill counts reproduce exactly: F05=28, F10=37, F15=42.
4. B27BB raw E20 reach counts reproduce from uncensored chronology: F05=17, F10=22, F15=24 pooled-major.
5. No result is promoted if any identity assertion fails.

## Frozen readout / selection rule
For every candidate report N, WR, PF, expectancy/trade, total PnL, E20 activation rate, hard-stop exits, ceiling exits, gap exits, and time exits by external/development/reference_validation/august and pooled-major.

A candidate is **formally eligible** only if, in each of external, development, and reference_validation separately:
- expectancy >= 0, and
- PF >= 1.0.

Among formally eligible candidates, select the highest pooled-major total PnL. If none qualifies, selection = NONE. Separately report the highest pooled-major PnL candidate as diagnostic only.

No live BBC changes. No regime, candle, confirmation, entry-depth, activation, runner, or additional threshold search is allowed in B27BC.