# ETH Economic-First E12 — Scientific Verdict

## Status
**ETH_ECONOMIC_FIRST_E12_NO_SEQUENCE_CANDIDATE**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- workflow run ID: **34487816747**
- job ID: **102906508382**
- head SHA: **62ab0b4b2d2bf23c0181afbee4decfe2bfd1b206**
- artifact ID: **10156522889**
- targeted workflow conclusion: **success**
- raw ETHUSDT 5m coverage: **100.0000%**

## Candidate universe
Exactly 1,080 clock-invariant sequence identities across three preregistered families:
- IRR: impulse → retrace → re-acceleration
- CE: compression → directional expansion
- ER: excursion → recovery → resume/extend-recovery

Each identity was evaluated separately across 48 half-hour UTC clock contexts. Clock was not a candidate coordinate. No H/L, breakout, EMA, Fibonacci, TP or SL was used.

## Formal result
**0 / 1,080 candidates passed the full Development breadth + median-economics + cross-era + clock-block gate.**
External and Reference Validation remained closed. No gate relaxation or second-best substitution was used.

## Family diagnostics
The failure modes differ materially by family:

### IRR
- Maximum Development evaluable clocks under the preregistered >=45 trades/clock rule: **0/48**.
- Therefore IRR was too sparse per fixed clock context for the E12 panel design to meaningfully judge its economic character.

### ER
- Maximum evaluable clocks: **9/48**.
- Maximum supportive clocks: **2**.
- Best broad-enough ER rows still had weak/negative median economics.
- ER is also materially sparse under fixed-clock slicing.

### CE
CE had enough occurrences to be evaluated more meaningfully in some configurations.
A descriptive narrow example was:
- CE / A1.5 / E0.35 / CONTINUE / LB480 / hold720
- evaluable clocks: **6**
- supportive clocks: **3/6**
- median WR: **54.76%**
- median expectancy: **+$1.39/trade**
- median PF: **1.349**
- median DD: **$63.76**
- but only **1/6** clock blocks passed, and cross-era behavior was not robust.

The most broadly evaluable CE configurations reached 42 clocks but had poor median WR/economics; for example CE / A1.5 / E0.35 / REVERSE / LB120 / hold360 had 42 evaluable clocks but only 6 supportive clocks, median WR 49.71%, median expectancy -$1.01, PF 0.723.

## Interpretation
E12 formally fails as preregistered, but it also exposes a design mismatch: sequence events are sparse and should be treated as **events that can occur at any time**, rather than requiring a large repeated sample inside each exact clock bucket.

This is not grounds to alter E12 post hoc. E12 stays closed exactly as run.

The scientifically clean next test is a new preregistered **E12B event-triggered sequence scan** using the exact same IRR/CE/ER shape definitions and parameter grids, but pooling causal event occurrences across time and using UTC clock blocks only as robustness strata. To avoid inflated overlapping observations, E12B should enforce a deterministic one-position-at-a-time/non-overlap rule per candidate. External and Reference Validation remain unopened until an E12B Development candidate passes its preregistered aggregate, annual, time-block and local-stability gates.