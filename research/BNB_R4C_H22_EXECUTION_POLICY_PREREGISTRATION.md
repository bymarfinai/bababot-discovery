# BNB R4c — H22 Plateau Execution Policy Preregistration

## Purpose
Convert the already-validated BNB R4b H22 plateau into one deterministic, auditable execution rule without selecting the best 2025 coordinate.

Parent scientific verdict: `BNB_R4B_FINAL_ROBUST_PLATEAUS_FOUND` on commit `7b66cec7c3f688e67eba38bf4a178824d7207e5e`.

## Frozen target
- Pair: BNBUSDT
- Direction: LONG only
- Habitat: H22 WIB
- Character: `RV_HIGH__RANGE_MID`
- R4b component rank: 3
- Frozen R4b cells:
  - LB180/H360
  - LB180/H480
  - LB180/H720
  - LB240/H720
  - LB360/H720
  - LB180/H960
  - LB240/H960

No cell may be added, removed, or re-ranked in R4c.

## Topology-derived execution policy
The policy is derived from plateau geometry only, not from 2025 cell PnL.

### Entry voters
The frozen plateau contains three unique lookback scales: **180, 240, 360 minutes**. Each unique lookback gets exactly one vote, preventing LB180 from receiving extra voting weight merely because it appears at more hold coordinates.

At each H22 quarter-hour anchor (22:00, 22:15, 22:30, 22:45 WIB = 15:00, 15:15, 15:30, 15:45 UTC), evaluate `RV_HIGH__RANGE_MID` independently at LB180, LB240 and LB360.

A LONG entry is eligible when **at least 2 of 3 lookback voters agree** at the same anchor.

### Daily de-duplication
- At most one new H22 position per WIB calendar day.
- If multiple H22 anchors qualify on the same day, use the **earliest qualifying anchor**.
- No pyramiding.
- No concurrent position overlap; a new entry is skipped if the previous policy position has not exited.

### Frozen hold
**Hold = 720 minutes (12 hours).**

Reason: H720 is the modal hold layer inside the frozen component and the only hold layer containing all three unique lookbacks LB180/LB240/LB360. This is a topology rule, not a performance selection.

### Execution mechanics
- Entry: engine anchor open used by the existing causal R4b engine.
- Exit: open exactly 720 minutes later.
- Notional: $500 fixed per trade.
- Base fee: $0.75 per round-trip trade, matching R4b.
- No TP/SL.
- No weekday optimization. The signal universe remains identical to the inherited R4b engine, which evaluates weekdays only.
- No coordinate fallback if the consensus rule underperforms.

## Historical window and scientific status
R4c scores only 2022-01-01 through 2025-12-31. Full earlier history may be retained only for causal indicator warm-up.

**2025 is NOT claimed as fresh OOS for R4c**, because this execution policy is being synthesized after the R4b 2025 plateau result was observed. R4c 2022-2025 is an execution-synthesis diagnostic.

**2026 remains CLOSED and must not be read, scored or used anywhere in this stage.**

## Required outputs
1. One true de-duplicated trade ledger.
2. Per-year metrics for 2022, 2023, 2024 and 2025.
3. Pooled 2022-2025 metrics.
4. Anchor usage and vote-count diagnostics.
5. Slippage stress at 0, 2, 5 and 10 bps **per side**.
6. Formal execution-policy verdict.

## Slippage stress
For stress level `b` bps per side, subtract a fixed round-trip implementation cost:

`$500 × (2 × b / 10,000)` per trade,

in addition to the frozen $0.75 fee.

## Frozen support gate
At **0 bps slippage**, each calendar year must satisfy:
- N >= 24 trades
- WR >= 52%
- Net > 0
- Expectancy > 0
- PF >= 1.15
- Max DD <= $160

Pooled 2022-2025 must satisfy:
- N >= 96
- WR >= 55%
- Net > 0
- Expectancy >= $0.50/trade
- PF >= 1.25
- Max DD <= $160

At **2 bps per side**:
- pooled Net > 0
- pooled Expectancy > 0
- pooled PF >= 1.15
- at least 3 of 4 calendar years have positive Net

Loss streak is retained as a risk-clustering diagnostic and is not a hard rejection gate.

### Verdicts
- PASS: `BNB_R4C_H22_EXECUTION_POLICY_SUPPORTED`
- FAIL: `BNB_R4C_H22_EXECUTION_POLICY_NOT_SUPPORTED`

The 5 bps and 10 bps results are stress diagnostics only and cannot rescue or invalidate the preregistered 0/2 bps gate.

## Prohibited after results
- changing 2-of-3 consensus to 1-of-3 or 3-of-3;
- changing H720 to H360/H480/H960;
- choosing a specific LB coordinate based on realized results;
- changing the earliest-anchor rule;
- adding TP/SL, weekday filters, additional states, SHORT, or leverage;
- opening 2026;
- searching alternative policies after seeing R4c output.

Research/shadow only.