# B27AR — BTC London->NY SHORT BLIND_F15 Partial-TP + Hybrid Runner — Preregistration

## Purpose
Test whether monetizing part of the SHORT move earlier can improve economics without changing the independently discovered F15 entry or adding a regime filter.

Frozen structure:
**Low K1 OPP0 -> causal leave -> BLIND F15 -> downside milestone -> take 50% fixed -> keep 50% as causal profit-lock runner.**

## Frozen cohort
Use exactly the B27AK/B27AN BLIND_F15 filled cohort:
- external 50
- development 79
- reference_validation 34
- august 1

Entry = F15 = L + 0.15R. No confirmation filter and no regime gate.

## Pre-milestone risk
Use the frozen B27AN D50 boundary:
- F65 = L + 0.65R
- invalidation only on completed raw 5m close strictly above F65
- exit at that actual completed close
- wick-only penetration does not invalidate.

## Frozen partial milestones
Search only the already-defined downside atlas levels:
- E05 = L - 0.05R
- E10 = L - 0.10R
- E15 = L - 0.15R
- E20 = L - 0.20R

No intermediate level may be introduced after results.

## Position split
At the first intrabar touch of the chosen milestone:
- 50% of the original $500 illustrative notional exits at the exact milestone price as a resting limit TP;
- the remaining 50% stays open as the hybrid runner;
- the split is fixed 50/50 for every candidate and is not searched.

If the milestone is touched intrabar on a bar that later closes above F65, the milestone touch occurs first chronologically. The 50% partial TP is credited and the runner activates; the later close does not retroactively cancel the intrabar milestone.

## Remaining 50% hybrid runner
Beginning with the NEXT raw 5m bar after milestone touch:
- resting profit ceiling starts at the milestone price;
- if bar open >= ceiling, exit remaining 50% at actual open;
- else if bar high >= ceiling, exit remaining 50% at ceiling;
- otherwise remain open;
- a strict 3-bar pivot high centered on the prior bar becomes known only at current bar close and may ratchet the ceiling DOWN for the next bar if that pivot high is below the active ceiling;
- ceiling never rises;
- no upper fixed stop remains after milestone activation;
- if no ceiling exit occurs by NY session end, exit remaining 50% at the exact session-end open.

## Economics
- total illustrative notional: $500
- first leg notional: $250
- runner leg notional: $250
- total round-trip fee for the complete split trade remains $0.40, charged once to combined trade PnL
- combined net PnL = partial gross PnL on $250 + runner gross PnL on $250 - $0.40
- if milestone never activates, whole $500 position follows pre-milestone F65 close invalidation or session-end exit.

## Outputs
For each milestone and partition report N, activation rate, combined WR, PF, expectancy/trade, total PnL, partial-leg PnL, runner-leg PnL, ceiling/gap/time exit counts, median runner capture/giveback, and median ratchets.

Also report pooled-major external+development+reference_validation.

## Frozen selection rule
A milestone is eligible only if in EACH external/development/reference_validation partition:
- expectancy >= 0
- PF >= 1.0

Among eligible milestones, select the one with highest pooled-major total net PnL. If none is eligible, report NONE.

Benchmarks:
- B27AN BLIND_F15 E20/D50 fixed baseline pooled-major total = -$11.666
- B27AQ full-position E20 profit-lock pooled-major total = -$15.058

## Mandatory assertions
1. B27AK F15 identities reproduce exactly 50/79/34/1 fills.
2. B27AN E20/D50 fixed baseline reproduces before interpretation.
3. Milestone geometry is exact for E05/E10/E15/E20.
4. Partial fill uses exactly 50% at exact milestone price.
5. Pre-milestone invalidation is completed-close F65 only.
6. Milestone intrabar touch precedes same-bar completed-close invalidation.
7. Runner ceiling is effective only from the next bar.
8. Runner ceiling can only move down.
9. Combined fee is exactly $0.40 per trade, not duplicated per leg.
10. No regime/confirmation/alternate stop/alternate split is introduced.

Research only. Live BBC unchanged.

CI execution-trigger edit only; no research semantics changed.
