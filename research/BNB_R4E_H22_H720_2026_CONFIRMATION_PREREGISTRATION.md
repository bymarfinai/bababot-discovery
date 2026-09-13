# BNB R4e — H22 H720 Frozen 2026 Confirmation Preregistration

## Purpose
Confirm the already-frozen BNBUSDT H22 execution candidate on data that did not participate in rule, coordinate, consensus, anchor, or hold selection.

This study is confirmation only. It is not a new discovery or optimization stage.

## Scientific lineage
- Frozen parent verdict: `232537c3006d09657e81538436115fc18d4a346c`
- Parent branch: `bnb-r4d-h22-hold-sweep`
- R4d status: `BEST_EXECUTION_CANDIDATE_NOT_FORMALLY_SUPPORTED`
- R4d selected duration: H720 / 720 minutes / 12 hours
- 2026 was closed throughout R4b/R4c/R4d selection.

## Frozen execution policy — immutable
- Pair: BNBUSDT
- Direction: LONG only
- Habitat: H22 WIB
- Candidate anchors: 22:00, 22:15, 22:30, 22:45 WIB (15:00, 15:15, 15:30, 15:45 UTC)
- Character: `RV_HIGH__RANGE_MID`
- Voter lookbacks: LB180, LB240, LB360
- Signal: at least 2 of 3 lookback voters must satisfy the frozen character
- Entry: earliest qualifying H22 anchor of the WIB day, using the inherited causal R4c entry-price convention
- Maximum positions: one position per WIB day
- No pyramiding / no overlapping position rescue
- Hold: exactly 720 minutes (12 hours)
- Exit: inherited causal R4c fixed-hold exit convention
- Notional: $500 per trade
- Base implementation fee: $0.75 per trade
- Slippage diagnostics: 0, 2, 5, 10 bps per side
- Signal universe: inherited weekday-only R4b/R4c universe
- No TP/SL overlay is introduced in R4e

No character threshold, voter set, consensus threshold, anchor, direction, hold, weekday rule, notional, fee, or exit rule may be changed after this preregistration.

## Freeze timestamp and two separate 2026 segments
R4e freeze timestamp: **2026-09-13T12:36:03+07:00** = **2026-09-13T05:36:03Z**.

Two segments must be reported separately:

1. **2026 pre-freeze historical OOS**
   - entry timestamp >= 2026-01-01T00:00:00Z
   - entry timestamp < freeze timestamp
   - only trades whose fixed 12h exit is fully observable are included
   - this is untouched strategy-specific historical OOS for the frozen R4d execution policy, but it is not called prospective because these dates predate this preregistration

2. **Post-freeze prospective shadow**
   - entry timestamp >= freeze timestamp
   - only fully completed 12h trades are scored
   - this segment may be extended by rerunning the identical frozen code later
   - no result in this segment may alter the frozen policy

The two segments must never be pooled for claims about prospective performance.

## 2026 formal confirmation gate
The historical annual 0-bps gate is inherited unchanged from R4c/R4d. A 2026 segment is formally mature only when N >= 24. Once mature, the 0-bps annual gate is:
- N >= 24
- WR >= 52%
- Net PnL > 0
- Expectancy > 0
- PF >= 1.15
- Max DD <= $160

The inherited 2-bps/side stress gate for the same segment is:
- Net PnL > 0
- Expectancy > 0
- PF >= 1.15

Slippage at 5 and 10 bps/side is descriptive stress only.

## Partial-year status logic
Because 2026 may have fewer than 24 qualifying trades at the first R4e run:

- If N >= 24 and both the inherited 0-bps annual gate and 2-bps stress gate pass: `BNB_R4E_2026_FORMAL_CONFIRMATION_PASS`.
- If N >= 24 and either inherited gate fails: `BNB_R4E_2026_FORMAL_CONFIRMATION_FAIL`.
- If N < 24, no formal pass/fail claim is allowed. Report `BNB_R4E_2026_SAMPLE_NOT_MATURE` plus the raw economics and whether all non-sample-size economic thresholds currently pass.

No minimum-N threshold may be lowered to manufacture a pass.

## Required outputs
- One true de-duplicated H720 execution ledger for 2026
- Separate pre-freeze and post-freeze ledger labels
- Entry timestamp, exit timestamp, WIB day, anchor, votes, active lookbacks, entry price, exit price, gross PnL, implementation costs, and net PnL at each slippage assumption
- Summary for pre-freeze historical OOS
- Summary for post-freeze prospective shadow
- Anchor usage diagnostics
- Frozen gate audit
- Exact latest fully observable trade timestamp / data cutoff

## Integrity rules
- 2022–2025 may be used only as frozen lineage/reference, not for further optimization.
- 2026 cannot select or alter any policy parameter.
- No rescue filters after seeing 2026.
- No cherry-picking of anchors or months.
- No reclassification of pre-freeze 2026 as prospective.
- Future reruns must use the same frozen code and append only newly completed trades.
- Research/shadow only; no guarantee of future profitability.
