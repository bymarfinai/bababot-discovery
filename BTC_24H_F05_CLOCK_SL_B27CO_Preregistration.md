# B27CO — BTC 24H F05 Clock-Specific Pre-T5 SL Economics — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test whether the remaining B27CN loss problem can be reduced by a **clock-specific causal pre-T5 stop**, while keeping the entry and every post-T5 rule frozen.

The user hypothesis is that different 4H clock zones may require different trade geometry. B27CO tests only the SL part of that hypothesis. **Entry remains F05 for all six clocks.** Entry tuning is explicitly forbidden in this experiment.

## Data-reuse caveat
B27CM/B27CN already inspected external and reference_validation behavior. Therefore B27CO external/reference_validation are reused-data confirmation only, **not untouched OOS**. Any positive result is only a research candidate and needs a genuinely fresh holdout before promotion.

## Frozen source and fill identity
Source: `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`, major partitions only, `eligible == True`.
Expected source identity: external 202 / development 333 / reference_validation 194 / pooled major 729.

Preserve B27CN entry semantics exactly. Expected executable fills must remain external 183 / development 297 / validation 172 / pooled major 652.

No clock, regime, weekday, or losing observation may be deleted.

## Frozen base architecture
For each event:
- `R4 = H-L`
- F05 entry reference = `L + 0.05*R4`
- `T5 = L - 0.05*R4`
- `T7.5 = L - 0.075*R4`
- `T10 = L - 0.10*R4`
- actual entry follows B27CN: F05 limit unless the first executable bar opens above F05, in which case actual open is used, provided open < H.

B27CN management remains frozen:
1. no BE at L or at rebreak;
2. completed close `<L` confirms rebreak;
3. milestone scanning starts next raw 5m bar after confirmation;
4. T5 earns L lock from next bar;
5. T7.5 earns T5 lock from next bar;
6. T10 earns T10 lock from next bar and enables the same strict 3-bar pivot-high runner;
7. if original block ends before T10, carry exactly +4h; if T10 was already reached, preserve original-block time exit;
8. catastrophic completed close `>H` remains valid whenever no protective ceiling has already exited the trade.

## Frozen SL candidates
To isolate SL from entry and preserve minimum nominal RR >=1:1, stops are defined from **actual fill price**, not from a fixed F-level:

- `S05`: stop threshold = `entry + 0.05*R4`; minimum geometric reward:risk to T10 is >=3:1.
- `S10`: stop threshold = `entry + 0.10*R4`; minimum geometric reward:risk to T10 is >=1.5:1.
- `S15`: stop threshold = `entry + 0.15*R4`; minimum geometric reward:risk to T10 is >=1:1.

`BASE_H` reproduces B27CN and is reported as the no-added-stop baseline; it is not an eligible new SL candidate.

No S20/S25 or wider fixed-risk candidate is allowed because it can violate the user's minimum nominal RR 1:1 relative to the frozen T10 objective.

## Causal stop semantics
The candidate stop is a **completed 5m close invalidation**, never an intrabar wick/touch stop.

Before T5 has been reached:
- first completed close strictly above `H` exits at that actual close as `FULL_SL_HIGH_BREAK`;
- otherwise first completed close strictly above the candidate stop threshold exits at that actual close as `PRE_T5_CLOSE_SL`.

If a bar both touches T5 intrabar and closes above the candidate stop threshold, `PRE_T5_CLOSE_SL` wins because T5 protection is not effective until the next bar. This prevents retroactive use of the favorable intrabar low.

Once T5 has been reached without a stop exit, the candidate pre-T5 stop is permanently disabled and B27CN's L/T5/T10 protection staircase takes over.

Fill-bar completed close may trigger High invalidation or the candidate stop. Same-fill-bar T5 is not credited, matching the frozen entry/rebreak chronology.

## Development-only clock selection
Evaluate `S05`, `S10`, and `S15` separately in each of the six UTC 4H clocks using **development only**.

For a candidate to qualify in a clock:
- development filled N >=30;
- expectancy/trade >0;
- PF >=1.10.

Among qualifying candidates select highest development expectancy. Tie-break: higher PF, then tighter stop in fixed order S05 -> S10 -> S15.

If none qualifies, select `BASE_H` for that clock. This is a fallback, not clock exclusion.

All candidate results must be reported even when they fail.

## Reused-data confirmation
After the six-clock development map is frozen, apply that exact map without changes to external and reference_validation.

For a clock's selected new stop to be called `REUSED_CONFIRMED`, require in both external and validation:
- filled N >=10;
- expectancy >0;
- PF >1.00.

Failure does not permit changing the stop or dropping the clock.

## Selected-map economics
Construct one all-clock map containing either the development-selected S05/S10/S15 or BASE_H fallback for every clock. Report development, external, validation, reused ext+val, and pooled major economics.

A selected-map reused-data candidate label requires:
1. source/fill/raw-data audit PASS and BASE_H reproduces B27CN within numerical tolerance;
2. development selected-map expectancy >0 and PF >=1.10;
3. external and validation selected-map expectancy >0 and PF >1.00 each;
4. pooled-major expectancy >0 and PF >=1.10;
5. no clock exclusion;
6. at least 3 of 6 clocks select a new SL rather than BASE_H.

Otherwise overall verdict is `B27CO_CLOCK_SL_NOT_SUPPORTED`.
If all conditions pass: `B27CO_CLOCK_SL_REUSED_CANDIDATE`.

`HIGH_QUALITY_70` is reported separately: economic WR >=70% in external, development, and validation. It does not override PF/expectancy.

## Required reporting
Six clocks first. For every clock show:
- development N, WR, PF, expectancy and net for BASE_H/S05/S10/S15;
- selected SL;
- reused external and validation WR/PF/expectancy for the selected rule;
- selected rule pre-T5 stop count, High-break count, T10 reached count.

Then selected-map economics: trades, fill rate, WR, PF, expectancy/trade, total net PnL, avg win/loss, max DD, max loss streak, stop counts, T10 reached, extension use.

Also report direct selected-map vs B27CN pooled-major and by partition.

Research only. Entry remains F05. Live BBC unchanged.

<!-- Execution trigger only; no semantic change. -->