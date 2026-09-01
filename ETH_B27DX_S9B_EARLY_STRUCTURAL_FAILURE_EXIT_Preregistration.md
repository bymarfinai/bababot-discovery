# ETH B27DX — S9B Early Structural Failure Exit — Preregistration

## Purpose
Test whether losses can be reduced after entry by exiting a failed continuation thesis earlier, without changing the frozen entry, target, or baseline invalidation geometry.

S9B is an **independent baseline-S4 exit test**. It does not depend on whether S9A succeeds. A later joint S9A+S9B experiment would require separate preregistration.

## Frozen baseline
- LONG only.
- R300 / X360.
- Entry F75.
- Target E25.
- Completed-close invalidation F20 remains active.
- Execution clocks: 05:00, 09:00, 10:00, 16:00 UTC.
- Same S4 candidate universe and global one-position lock logic.
- External / Development / Reference Validation.
- 0 bps primary and 5 bps stress.

## S9B structural scratch rule — frozen before results
For each filled trade, freeze the completed K1 leave-bar close (`leave_close`), which is known before the F75 entry can occur.

Beginning with the first **completed raw 5m bar after the entry bar**:
1. Existing fixed target E25 keeps first precedence.
2. Existing completed-close F20 invalidation remains active.
3. Until H has been revisited after entry, if a completed bar has `high < H` and `close < leave_close`, exit at that completed close with reason `EARLY_STRUCTURAL_FAILURE`.
4. Once any completed post-entry bar has `high >= H`, the structural scratch condition is permanently disarmed for that trade; the trade thereafter uses only the frozen target/F20/time-exit logic.

If a bar both revisits H and closes below leave_close, the H revisit disarms the scratch rule for that bar; no intrabar ordering assumption is made.

There is no time cutoff, distance sweep, alternate leave threshold, break-even move, or partial exit in S9B.

## Causal execution
- Leave close is known before entry.
- Exit decisions use completed 5m bars only.
- Same S4 completed-close execution convention is used.
- Candidate exits are rescored before global portfolio locking because shortened holding periods can free later candidates.

## Frozen support gate
S9B is called `SUPPORTED` only if all are true:
1. Baseline rescore parity and leave chronology audit pass.
2. S9B 0 bps portfolio has PF > 1 and net > 0 in External, Development, and Reference Validation separately.
3. S9B pooled-major 5 bps PF > 1 and net > 0.
4. Pooled-major 0 bps PF, expectancy, and net are each strictly higher than S4 baseline.
5. Mean absolute loss on losing accepted trades is strictly smaller than S4 baseline.

BTC WR/PF/expectancy are diagnostic only and not required for S9B support.

## Required outputs
- baseline vs S9B metrics by partition and pooled-major,
- number/share of structural-failure exits,
- what fraction of baseline losses are cut earlier,
- mean/median losing PnL before vs after,
- accepted trades/week after re-lock,
- newly freed trades due shorter lock duration,
- 5 bps stress,
- parity/causal audit,
- written verdict.

## Guardrails
- No S9A freshness rule in this experiment.
- No alternate leave-close threshold.
- No target/stop/runner tuning.
- No leverage or position sizing change.
- No live-code change.
