# ETH Native London->New York Entry Discovery — Z4 Preregistration

## Purpose
Discover the most robust causal LONG entry mode after the ETH-native London->NY lineage has produced:
1. frozen Z1 clock: reference 18:30-00:00 WIB, execution 00:00-06:30 WIB;
2. causal High K1 OPP0 touch and completed leave;
3. shallow retest cohort F95 or F90;
4. completed 5m breakout close strictly above reference High (`B00`).

This milestone answers only: **after B00 is known, where/how should entry be taken?**

No TP/SL, fee, leverage, PnL, PF, expectancy, or live promotion is allowed.

## Important lineage note
Z3's preregistered selected threshold was B100 and it did not replicate. Z3 nevertheless showed B00 as the broadest/most stable completed-close breakout candidate across periods. The user explicitly approved continuing with B00. Therefore Z4 treats B00 as a **lineage-conditioned exploratory breakout candidate**, not as a retrospectively re-labelled Z3 validated winner.

## Frozen upstream structure
- ETHUSDT Binance Futures raw 5m only.
- Reference start 11:30 UTC / 18:30 WIB.
- Reference duration 5h30 = 66 raw 5m bars.
- Execution duration 6h30 = 78 raw 5m bars.
- LONG only.
- Weekday execution start.
- Same external / development / reference_validation partitions.
- Raw 5m coverage >=99.5%.
- H=max(reference high), L=min(reference low), R=H-L.
- Reuse Z2 K1/OPP0, contiguous-touch, leave, and F95/F90 retest chronology exactly.
- B00 = first completed 5m close strictly >H after the completed retest.
- B00 is known only at breakout-bar close.

## Frozen entry modes
Evaluate each F95 and F90 cohort independently.

### 1. `BREAKOUT_CLOSE_BENCHMARK`
- Structural benchmark only, not automatically promotable as executable.
- Entry timestamp = B00 completed timestamp.
- Entry price = breakout candle close.
- Used to quantify the theoretical cost of acting exactly when the completed breakout becomes known.

### 2. `NEXT_OPEN`
- First directly executable mode.
- Entry timestamp = start of the immediately following raw 5m bar after the breakout candle completes.
- Entry price = that bar's open.
- If no next raw 5m bar exists strictly before execution end, entry is unavailable.

### 3. `H_RETEST_LIMIT`
- Search begins on the first raw 5m bar after B00 completes.
- First later bar with `low <= H` fills a LONG limit at exactly H.
- Same breakout bar can never fill this entry.
- If `close < L` occurs before fill, entry is cancelled.
- If execution ends before fill, entry is unavailable.
- If a bar both trades H and later closes <L, H fill is credited because the limit is executable intrabar before the completed close is known; the subsequent close is path information, not pre-fill hindsight.

### 4. `H_REBREAK_NEXT_OPEN`
- Search begins after B00 completes.
- First require a later completed bar with `close <= H` (back-in-range / H retest confirmation).
- After that, require the first later completed bar with `close > H` (confirmed re-break).
- Entry is at the immediately following raw 5m bar open.
- If `close < L` before the re-break entry, cancel.
- No same-bar back-in-range and re-break ordering is inferred.
- If no next raw bar exists before execution end, unavailable.

## Structural quality checkpoints — diagnostic only
These are **not profit targets** and cannot be promoted to TP in Z4.

For every available entry, from the entry timestamp through execution end, measure whether price later reaches:
- C05 = H + 0.05R
- C10 = H + 0.10R
- C20 = H + 0.20R

For `BREAKOUT_CLOSE_BENCHMARK`, checkpoint evaluation begins on the next raw 5m bar after the breakout close; the breakout bar itself cannot retrospectively satisfy a post-entry checkpoint.
For all other modes, checkpoint evaluation starts from the entry bar inclusive because entry price is known at its open or intrabar H limit.

Also measure:
- entry participation rate among B00 cases;
- entry price fraction `(entry_price-L)/R`;
- max favorable fraction after entry;
- min adverse fraction after entry;
- adverse distance in R from entry to subsequent minimum;
- median minutes to each checkpoint;
- fraction that closes <L before C20;
- unresolved by execution end.

## Development-only selection rule
Selection sees development only and only the three executable modes (`NEXT_OPEN`, `H_RETEST_LIMIT`, `H_REBREAK_NEXT_OPEN`). `BREAKOUT_CLOSE_BENCHMARK` cannot win selection.

A mode is a development candidate only if for **both F95 and F90 independently**:
- >=35 available entries;
- participation rate among B00 cases >=40%;
- C10 reach rate among available entries >=60%;
- C20 reach rate among available entries >=45%;
- C20 reaches > close<L-before-C20 failures.

Among candidates choose using this frozen lexicographic rule:
1. highest minimum C20 reach rate across F95/F90;
2. then highest minimum C10 reach rate;
3. then lower median entry fraction (better price);
4. then higher minimum participation rate;
5. tie-break priority: `H_RETEST_LIMIT`, `NEXT_OPEN`, `H_REBREAK_NEXT_OPEN`.

## Historical replication gate
The selected development entry mode is `SUPPORTED` only if in **external and reference_validation**, for **both F95 and F90 independently**:
- >=20 available entries;
- participation >=30%;
- C10 reach >=55%;
- C20 reach >=40%;
- C20 reaches > close<L-before-C20 failures.

No pooled rescue. No switching to a different entry mode after holdout inspection.

## Mandatory assertions
1. F90 B00 sessions are a subset of F95 B00 sessions.
2. Every B00 close is strictly >H and strictly after its completed retest.
3. NEXT_OPEN timestamp is exactly one raw 5m bar after B00 bar start.
4. H_RETEST_LIMIT cannot fill on the B00 bar.
5. H_REBREAK_NEXT_OPEN requires completed close<=H, then later completed close>H, then next-bar open.
6. No entry timestamp is after execution end.
7. C20 reach implies C10 and C05 reach.
8. C10 reach implies C05 reach.
9. Selection uses development only.
10. No TP/SL/PnL/economic output is produced.

Research only. Stop after Z4.