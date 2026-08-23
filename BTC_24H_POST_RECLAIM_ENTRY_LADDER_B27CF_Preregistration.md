# B27CF — BTC 24H Post-Reclaim SHORT Entry Ladder — Preregistration

## Purpose
Find the best structural SHORT limit location after the exact B27CE first-retest reclaim cohort, before any later Low rebreak. This is anatomy/entry-geometry only; it does not define stop, TP, fee, PF, PnL, expectancy, or a live rule.

## Frozen source cohort
Source: `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`.

Use only major partitions and exact B27CE rows with `eligible == True`. Identity before any level filter must reproduce:
- external eligible 202
- development eligible 333
- reference_validation eligible 194
- pooled OOS eligible 396
- pooled major eligible 729.

The 5 no-followthrough-window rows are excluded because no causal post-reclaim bar exists.

## Frozen entry ladder
Re-use the exact descriptive B27CE levels; no new levels may be introduced:
- F05 = `L + 0.05*R4`
- F10 = `L + 0.10*R4`
- F15 = `L + 0.15*R4`
- F25 = `L + 0.25*R4`
- F50 = `L + 0.50*R4`
where `R4 = H-L`.

The reclaim is confirmed at `reclaim_complete_ts`. Evaluation starts on the next raw 5m bar at that timestamp and ends at the same 4H block end.

For each level independently, the first raw 5m bar with `high >= entry_px` is the structural fill. A fill is valid only if it occurs before any completed strict `close < L` or `close > H` terminal that happened on an earlier bar. If the fill bar itself closes below L, that counts as rebreak-after-fill because fill-by-high is known before the completed close is observed.

After a valid fill, classify the first completed strict boundary close through block end:
- `REBREAK_LOW_AFTER_FILL`: first `close < L`;
- `HIGH_BREAK_AFTER_FILL`: first `close > H`;
- `NO_BOUNDARY_AFTER_FILL`: neither by block end.

No later bar can alter the class.

## Required metrics
For each level, report external, development, validation, pooled OOS, pooled major, and each 4H clock:
- source N;
- fills N / fill rate;
- rebreak-after-fill N / rate;
- high-break-after-fill rate;
- no-boundary-after-fill rate;
- median reclaim-confirmation -> fill minutes;
- median fill -> Low rebreak minutes among rebreak cases.

These are structural rates, not trading WR.

## Frozen development selection
A level is development-eligible only if:
- development fills >= 50; and
- development rebreak-after-fill rate >= 70%.

Among development-eligible levels, select the **highest entry fraction** (best SHORT price) as the frozen candidate.

Untouched OOS support requires the selected level to have:
- external fills >= 30 and rebreak/fill >= 60%;
- reference_validation fills >= 30 and rebreak/fill >= 60%;
- pooled OOS fills >= 70 and rebreak/fill >= 65%.

If no development level is eligible, verdict is `B27CF_POST_RECLAIM_ENTRY_NONE`.
If selected level fails OOS support, verdict is `B27CF_POST_RECLAIM_ENTRY_NOT_SUPPORTED`.
If it passes, verdict is `B27CF_POST_RECLAIM_ENTRY_SUPPORTED`.

No economic implication follows. Any supported structural entry still requires a separately preregistered RR>=1:1 economic test.