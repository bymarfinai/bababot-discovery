# ETH Native London->New York Entry Discovery — Z4 Preregistration

**PREREGISTERED before result-bearing execution.**

## Purpose
Discover the most robust causal LONG entry mode after the ETH-native lineage has produced: Z1 clock 18:30-00:00 WIB reference / 00:00-06:30 WIB execution; High K1 OPP0; completed causal leave; shallow F95 or F90 retest; then B00 = first completed 5m close strictly above H.

Z4 answers only: **after B00 is known, where/how should entry be taken?** No TP/SL, fee, leverage, PnL, PF, expectancy, or live promotion.

## Lineage note
Z3's preregistered winner was B100 and it failed replication. Z3 nevertheless showed B00 as the broadest completed-close breakout candidate. The user explicitly approved continuing with B00. Z4 therefore treats B00 as a **lineage-conditioned exploratory candidate**, not a retrospectively relabelled Z3 validated winner.

## Frozen structure
- ETHUSDT Binance Futures raw 5m; coverage >=99.5%.
- Reference 11:30-17:00 UTC = 18:30-00:00 WIB, 66 bars.
- Execution 17:00-23:30 UTC = 00:00-06:30 WIB, 78 bars.
- LONG only; weekday execution start; same external/development/reference_validation partitions.
- H=max(reference high), L=min(reference low), R=H-L.
- Reuse Z2 K1/OPP0, contiguous touch, leave, and F95/F90 retest chronology exactly.
- B00 is the first completed 5m close >H after completed retest and is known only at that bar close.

## Frozen entry modes
Evaluate F95 and F90 independently.

### `BREAKOUT_CLOSE_BENCHMARK`
Structural benchmark only; cannot win selection. Entry timestamp=B00 completed timestamp; price=breakout close.

### `NEXT_OPEN`
Enter at the open of the immediately following raw 5m bar after B00 completes. If that bar does not exist strictly before execution end, unavailable.

### `H_RETEST_LIMIT`
Starting with the first raw bar after B00, wait for first bar with low<=H and fill a LONG limit at exactly H. B00 bar cannot fill. If a completed close<L occurs on an earlier bar, cancel. If the fill bar itself later closes<L, the fill still counts because the limit was executable intrabar before the completed close became known. To avoid intrabar ordering ambiguity, **continuation checkpoints and MFE begin only on the next raw 5m bar after the fill bar**.

### `H_REBREAK_NEXT_OPEN`
After B00, first require a later completed close<=H. Then require a strictly later completed close>H. Enter at the immediately following raw 5m open. A close<L before the re-break entry cancels. Same-bar back-in-range/re-break ordering is forbidden. If no next bar exists before execution end, unavailable.

## Fixed structural checkpoints — diagnostic only
These are measurement anchors, **not TP candidates**:
- C05 = H+0.05R
- C10 = H+0.10R
- C20 = H+0.20R

Evaluation chronology:
- BREAKOUT_CLOSE_BENCHMARK: from the next raw bar after B00.
- NEXT_OPEN and H_REBREAK_NEXT_OPEN: from the entry bar inclusive, because entry is known at the bar open.
- H_RETEST_LIMIT: from the raw bar after the fill bar.

A checkpoint is counted as a **post-entry reach only if entry_price < checkpoint_price** and a permitted evaluation bar subsequently has high>=checkpoint. If entry is already at/above a checkpoint, that checkpoint is recorded `ALREADY_PASSED_AT_ENTRY` and does not count as post-entry continuation.

On an evaluation bar, a checkpoint high-touch is credited before a same-bar completed close<L, because the close occurs at bar end. C20 implies C10/C05 and C10 implies C05.

Also report participation among B00 cases, entry fraction `(entry-L)/R`, MFE/MAE fractions, adverse distance in R, checkpoint times, close<L-before-C20, and unresolved cases. These are structural diagnostics only.

## Development-only selection
Only executable modes can win: NEXT_OPEN, H_RETEST_LIMIT, H_REBREAK_NEXT_OPEN.

A mode is a development candidate only if **both F95 and F90 independently** have:
- >=35 available entries;
- participation >=40% of B00 cases;
- post-entry C10 reach >=60%;
- post-entry C20 reach >=45%;
- C20 reaches > close<L-before-C20 failures.

Choose among candidates lexicographically, frozen before holdout inspection:
1. highest minimum C20 reach across F95/F90;
2. highest minimum C10 reach;
3. lower median entry fraction;
4. higher minimum participation;
5. tie priority H_RETEST_LIMIT, NEXT_OPEN, H_REBREAK_NEXT_OPEN.

## Historical replication
The selected development mode is SUPPORTED only if **external and reference_validation**, for **both F95/F90 independently**, each have:
- >=20 available entries;
- participation >=30%;
- C10 reach >=55%;
- C20 reach >=40%;
- C20 reaches > close<L-before-C20 failures.

No pooled rescue and no switching winner after holdout inspection.

## Assertions
1. F90 B00 sessions subset of F95 B00 sessions.
2. Every B00 close >H and occurs strictly after completed retest.
3. NEXT_OPEN is exactly the immediately following raw bar.
4. H_RETEST_LIMIT never fills on B00 bar and checkpoint evaluation excludes fill bar.
5. H_REBREAK_NEXT_OPEN requires close<=H, later close>H, then next open.
6. No entry after execution end.
7. Checkpoint monotonicity holds.
8. Selection sees development only.
9. No economic output.

Research only. Stop after Z4.