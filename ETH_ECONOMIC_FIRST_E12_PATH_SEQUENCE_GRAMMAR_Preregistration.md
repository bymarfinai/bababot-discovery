# ETH Economic-First E12 — Path-Sequence Grammar Preregistration

## Purpose
Test whether ETH has a repeatable economic character in the **order of movement inside the pre-entry path**, rather than in a magic clock, H/L level, or scalar state bin.

E12 tests exactly three preregistered sequence families requested before result exposure:
1. **Impulse → retrace → re-acceleration (IRR)**
2. **Compression → directional expansion (CE)**
3. **Excursion → recovery → resume/extend-recovery (ER)**

Clock is context only. Candidate identity does **not** include clock.

## Frozen data / economics
- ETHUSDT Binance Futures raw 5m OHLC.
- Development partition only for discovery/selection: same `base.PARTS['development']` lineage used by E9–E11.
- External and Reference Validation stay closed unless one Development candidate passes all preregistered gates and is interior.
- Weekdays only, exact 5m open timestamps.
- $500 fixed notional.
- $0.75 round-trip fee.
- No compounding, no extra slippage.
- Gross long return: `500 * (exit-entry)/entry`; short is the exact linear symmetric negative direction of that return.
- Net PnL = gross PnL − $0.75.
- Net win iff net PnL > 0.
- No TP / no SL; exact-open time exit only.

## Clock contexts
All 48 half-hour UTC clocks are evaluated separately. Clock can never be selected as part of a candidate. A candidate must work across many clock contexts.

## Path horizons and exit holds
Exit holds for all families: `120, 240, 360, 720, 960 minutes`.
All path features use only open prices from the preregistered lookback ending at the entry open. No future bar information enters the event definition. IRR and ER leg returns use log returns so leg ratios are additive and directionally symmetric.

## Family 1 — IRR
Lookbacks: `60, 120, 240, 360m`.
Split the lookback into three equal chronological legs, producing log returns `r1, r2, r3`.
A valid event requires:
- `r1 != 0`,
- `sign(r2) = -sign(r1)`,
- `sign(r3) = sign(r1)`,
- retrace ratio `abs(r2)/abs(r1)` in one of three fixed bands:
  - `R1 = [0.15, 0.40)`
  - `R2 = [0.40, 0.65)`
  - `R3 = [0.65, 0.90]`
- re-acceleration ratio `abs(r3)/abs(r1) >= q`, with `q ∈ {0.25, 0.40, 0.55}`,
- the final entry price remains on the impulse side of the path start.

Base direction = sign of `r1`.
Modes: `CONTINUE` or `REVERSE`.
Candidate count: `4 × 3 × 3 × 2 × 5 = 360`.

## Family 2 — CE
Lookbacks: `120, 240, 360, 480m`.
Split the path at 2/3 of the lookback: first 2/3 compression segment, last 1/3 expansion segment.
For each segment compute mean absolute log-return per 5m step.
A valid event requires:
- expansion/compression activity ratio `>= a`, where `a ∈ {1.5, 2.0, 3.0}`,
- expansion directional efficiency `abs(expansion net log move) / sum(abs(expansion step log moves)) >= e`, where `e ∈ {0.35, 0.50, 0.65}`,
- non-zero expansion net direction.

Base direction = expansion net direction.
Modes: `CONTINUE` or `REVERSE`.
Candidate count: `4 × 3 × 3 × 2 × 5 = 360`.

## Family 3 — ER
Lookbacks: `60, 120, 240, 360m`.
Split the path into equal first and second halves. First-half log return is the excursion leg; second-half log return is the recovery leg.
A valid event requires:
- non-zero first-half excursion,
- second-half move opposite the excursion,
- first-half directional efficiency `>= e`, `e ∈ {0.35, 0.50, 0.65}`,
- recovery ratio `abs(second-half return)/abs(first-half return)` in:
  - `R1 = [0.20, 0.40)`
  - `R2 = [0.40, 0.60)`
  - `R3 = [0.60, 0.80]`,
- entry remains on the original excursion side of the path start.

Base direction = original excursion direction.
Modes: `RESUME` or `EXTEND_RECOVERY`.
Candidate count: `4 × 3 × 3 × 2 × 5 = 360`.

## Total candidate identities
Exactly **1,080** candidate identities. Each is evaluated across all 48 clock contexts. Candidate identity never includes clock.

## Development clock-level evaluation
A candidate-clock is evaluable when it has at least **45 trades** in Development.
A candidate-clock is supportive when evaluable and all are true:
- WR >= **54%**,
- net PnL > 0,
- expectancy >= **+$0.50/trade**,
- PF >= **1.15**,
- max DD <= **$100**,
- max loss streak <= **8**.

## Candidate breadth gate
Across the 48 clock contexts:
- evaluable clocks >= **24**,
- supportive clocks >= **14**,
- supportive fraction >= **55%** of evaluable clocks,
- positive-expectancy clocks >= **28**.

## Median economic gate
Across evaluable clocks:
- median WR >= **55%**,
- median expectancy >= **+$0.75/trade**,
- median PF >= **1.20**,
- median DD <= **$90**.

## Cross-era gate
For each of 2022, 2023, 2024 separately, using candidate-clock observations with >=12 trades in that year:
- evaluable clocks >= **20**,
- median WR >= **52%**,
- median expectancy >= **+$0.25/trade**,
- fraction of evaluable clocks with positive expectancy >= **55%**.
All three years must pass.

## Clock-block breadth
Split UTC into six fixed four-hour blocks. A block is supportive if at least half of its evaluable clocks are supportive under the Development clock-level rule. Require **>=4/6 supportive clock blocks**.

## Development selection
A candidate passes only if breadth + median economics + all three eras + clock-block breadth all pass.
Rank passing candidates lexicographically by:
1. highest minimum annual median expectancy,
2. highest supportive fraction,
3. highest median expectancy,
4. highest median WR,
5. highest median PF,
6. lower median DD,
7. shorter hold,
8. shorter lookback,
9. stable family/parameter lexical tie-break.
No raw-top substitution if zero candidates pass.

## Boundary handling
A selected candidate is boundary-open if its lookback or hold is at that family/grid minimum or maximum, or an ordinal numeric shape parameter is at its minimum/maximum tested level. The middle band/threshold values are interior. Boundary winner does **not** open OOS; it requires a new preregistered refinement.

## Holdout gate if an interior winner exists
Freeze the exact candidate identity. Evaluate across all 48 clock contexts separately in External and Reference Validation.
Each holdout must have:
- evaluable clocks >= **16** (>=25 trades per evaluable clock),
- median WR >= **53%**,
- median expectancy > **0**,
- median PF >= **1.08**,
- positive-expectancy fraction >= **55%**,
- supportive clock blocks >= **4/6**, where supportive holdout clock means WR>=52%, expectancy>0, PF>=1.05.
Both holdouts must pass unchanged. No second-best candidate, no gate relaxation, no post-hoc coordinate change.

## Interpretation discipline
- Clock-panel PnL is diagnostic and overlapping contexts are **not** claimed as portfolio-return totals.
- E12 is research/shadow only.
- A Development pass is not a live trading claim.
- If no candidate passes, these three sequence grammars are closed in their preregistered form; do not rescue them by lowering thresholds.