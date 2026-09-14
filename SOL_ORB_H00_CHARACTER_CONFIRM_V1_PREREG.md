# SOL ORB H00 Character Confirmation v1 — Preregistration

## Purpose
Confirm the frozen SOL structural character discovered on Development 2022–2024 without changing thresholds and without opening Reference Validation 2025–2026.

## Frozen candidate
- Symbol: SOLUSDT
- Direction: LONG only
- Anchor session: 17:00 UTC = 00:00 WIB
- ORB: first 15 minutes (3 x 5m bars)
- Required ORB range: >= 0.50% of session first-bar open
- Upside breakout above ORB High
- Retest of ORB High within 30 minutes
- Retest must show bullish reaction and close above anchored VWAP
- Small BOS must occur within next 3 x 5m bars and close above ORB High and anchored VWAP
- Acceptance requirement: BOS close >= 0.50% above ORB High
- Entry: next 5m open after BOS close
- Diagnostic exit: fixed +60 minutes
- Reference notional: USD 500/trade
- Roundtrip cost: 0.15%
- Weekdays only
- Maximum one event per anchor session

## Confirmation data
- External confirmation only: 2020-01-01 <= timestamp < 2022-01-01
- Development 2022–2024 is not re-optimized.
- Reference Validation 2025-01-01 through 2026-07-30 remains CLOSED.
- August 2026 remains CLOSED.

## No-tuning rule
This confirmation run must not change the anchor hour, ORB duration, 0.50% ORB threshold, 0.50% acceptance threshold, VWAP definition, BOS definition, reaction definition, entry timing, or 60-minute exit.

## Decision gate
- PASS: total confirmed trades >= 10, net WR >= 60%, net PnL > 0, and profit factor > 1.0.
- INCONCLUSIVE: total confirmed trades < 10, regardless of apparent WR/PF.
- FAIL: N >= 10 but any PASS economics gate is not met.

Year-by-year 2020/2021 statistics are reported as stability diagnostics only and are not used to change the frozen rule.

## Interpretation
A PASS nominates this as a confirmed SOL structural character and permits moving to the next anchor hour. It does not authorize opening Reference Validation or TP/SL optimization.
