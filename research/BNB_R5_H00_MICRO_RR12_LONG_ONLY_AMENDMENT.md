# BNB R5 H00 — Micro RR 1:2 LONG-Only Amendment

## Scope change before valid result use
This amendment supersedes only the direction scope of the original BNB R5 H00 preregistration.

The user explicitly requested **LONG only** before any result from the original LONG+SHORT run was accepted or used.

The original run **34739787820** (job **103677426482**) was launched under the obsolete LONG+SHORT scope and is therefore **INVALID / SUPERSEDED for scientific interpretation**, regardless of whether it later completes. Its economic outputs must not be used for selection, tuning, ranking, or commentary on the LONG-only study.

## Frozen LONG-only scope
- Pair: BNBUSDT
- Habitat: 00:00–01:00 WIB only
- Anchors: 00:00, 00:15, 00:30, 00:45 WIB
- Direction: **LONG only**
- Entry: anchor open using only information available at that instant
- TP: +0.30%
- SL: -0.15%
- Nominal RR: 1 risk : 2 reward
- Max holds: 15, 30, 60, 90, 120 minutes
- Same-5m TP/SL ambiguity: SL-first
- Timeout: exit at open at the max-hold timestamp
- Notional: $500/trade
- Fee: $0.75/trade
- Slippage stress: 0, 2, 5, 10 bps per side
- Weekday-only universe retained for comparability

## Frozen LONG-only search space
- Lookbacks: 15, 30, 60, 120, 240, 360 minutes
- Character grammar: existing causal 90-rule set
- Direction: LONG only
- Max holds: 15, 30, 60, 90, 120 minutes
- Total cells: **6 × 90 × 1 × 5 = 2,700**

## Unchanged protocol
Everything else from `BNB_R5_H00_MICRO_RR12_PREREGISTRATION.md` remains frozen and unchanged:
- development/ranking uses 2022–2024 only;
- only the #1 development-ranked LONG cell may be opened on 2025;
- 2026 remains closed;
- development eligibility thresholds are unchanged;
- formal high-WR target remains pooled TP-first >=80% and minimum annual TP-first >=75%, plus the original economics/stress gates;
- ranking order remains unchanged except that the obsolete direction tie-break is irrelevant because only LONG exists;
- no TP/SL, character, lookback, anchor, max-hold, fee, slippage, or gate relaxation is permitted after results are observed.

Research/shadow only; no guarantee of future profitability.
