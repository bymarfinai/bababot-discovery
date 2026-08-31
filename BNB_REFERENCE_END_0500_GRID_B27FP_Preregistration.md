# BNB Fixed 05:00 WIB Reference-End Grid — B27FP Preregistration

## Purpose
Test whether the strong BNB structure seen in B27FO is primarily associated with a common 05:00 WIB reference-end / 05:00–09:00 WIB execution habitat rather than one exact reference duration.

## Frozen universe
- Symbol: BNBUSDT
- Source: existing repository 5m loader only
- Common normalized local dates: 2022-01-02 through 2024-12-31 inclusive
- Timezone: Asia/Jakarta
- All weekdays
- Raw coverage gate: >=99.5%
- No external/reference-validation/August/holdout data

## Frozen state machine
Use the exact inherited causal LONG classifier from the B27EM/B27FN/B27FO lineage without modification.

## Fixed execution geometry
- Reference end: exactly 05:00 WIB
- Execution start: exactly 05:00 WIB
- Execution end: exactly 09:00 WIB
- Execution duration: 4 hours

## Preregistered reference-start grid
Every range ends at 05:00 WIB:
1. 00:00–05:00 (5.0h)
2. 00:30–05:00 (4.5h)
3. 01:00–05:00 (4.0h)
4. 01:30–05:00 (3.5h)
5. 02:00–05:00 (3.0h)
6. 02:30–05:00 (2.5h)

No additional start times may be added after results are observed inside B27FP.

## Mandatory reproduction gates
Before interpreting new cells, exact inherited cells must reproduce:
- 01:00–05:00: 1095 sessions, 162 causal leaves, 132 H2
- 02:00–05:00: 1095 sessions, 167 causal leaves, 135 H2
Any mismatch aborts the milestone.

## Reported metrics per cell
- sessions
- K1 qualified
- causal leaves
- H2 arrivals
- H2/leave structural rate
- opposite breaks before H2
- no H2 by execution end
- resolved H2 share
- median leave→H2 minutes

H2/leave is a structural rate, not trading win rate.

## Frozen zone diagnostics
A grid point is HIGH_STRENGTH if:
- causal leaves >=100, and
- H2/leave >=75%.

Report the longest contiguous HIGH_STRENGTH start-time region.

Classification:
- `BROAD_0500_REFERENCE_END_ZONE` if the longest contiguous HIGH_STRENGTH region contains at least 4 of the 6 preregistered starts.
- `SHARP_START_PREFERENCE` if fewer than 3 contiguous starts are HIGH_STRENGTH.
- `MIXED_0500_REFERENCE_END_ZONE` otherwise.

Also report overall max-minus-min H2/leave spread and rank all six cells, but do not select a trading rule.

## Interpretation boundary
B27FP is a structural fixed-boundary diagnostic only. No entry, TP, SL, PnL, fees, slippage, weekday selection, or holdout evaluation is allowed.

STOP after producing the preregistered grid and classification.
