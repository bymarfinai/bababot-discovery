# ETH London -> New York M15 M14-Management × Target-Family Economics — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Select the best economically robust target inside the already-supported M7 target family while freezing the M14 management rule.

M15 does **not** search a new entry, stop, level, timing rule, indicator, or management state.

## Frozen setup
- ETHUSDT perpetual, raw 5m.
- Exact M5 F90 EARLY_RECLAIM executed cohort: 95 setups.
- Original F90 EARLY_RECLAIM entry unchanged.
- Hard invalidation: first completed 5m close < F50.
- Session-end exit unchanged.
- $500 notional, $0.40 round-trip fee model.
- 0bps and 5bps stress.

## Frozen M14 management
- F75 = L + 0.75R.
- H2 = first later arrival to H (`high >= H`) under the frozen lifecycle.
- If the **first completed close < F75 occurs after H2 has already occurred or on the H2 bar**, exit the full position at the **next raw 5m open**.
- If F75 is breached before H2, do nothing; the trade remains on the target/F50/session lifecycle.
- Target takes precedence if already traded on the signal bar; completed-close F50 invalidation also precedes the conditional F75 exit.
- No re-entry, partial cut, trailing stop, post-breakout floor, add-back, or timeout.

## Frozen target family
Only the M7-supported structural targets are eligible:
1. E05 = H + 0.05R
2. E10 = H + 0.10R
3. E15 = H + 0.15R

For audit/comparison, the corresponding unmanaged E05/F50, E10/F50, and E15/F50 baselines are also reproduced. Baselines are diagnostic only and cannot be promoted.

No E06/E08/E12/E20 or other target may be added after result inspection.

## Metrics
Report by external / development / reference_validation / pooled-major:
- N, WR, PF, expectancy, net, max loss streak;
- 5bps WR/PF/expectancy/net;
- conditional-exit count;
- number of baseline losers/winners affected;
- delta versus same-target unmanaged baseline.

## Mandatory audits
1. 95-row cohort parity.
2. Raw ETH 5m coverage >=99.5%.
3. Exact M8 parity for unmanaged E05/F50, E10/F50, and E15/F50 exits and PnL.
4. Exact M14 parity for managed E15 (`F75_POST_H2_EXIT`).
5. Conditional exit acts only at the next 5m open after completed-close F75 breach with H2 already seen.
6. At most one result row per setup × variant.

## Frozen promotion screen
A managed target is supported only if all are true:
1. Audit PASS.
2. Every major partition N >= 15.
3. Every major partition WR >= 70% at 0bps.
4. Every major partition PF > 1.00 and net > 0 at 0bps.
5. Development 5bps PF > 1.00 and net > 0.
6. Pooled-major WR >= 72% at 0bps.
7. Pooled-major PF >= 1.30 and net > 0 at 0bps.
8. Pooled-major 5bps PF > 1.10 and net > 0.

If multiple managed targets pass, rank by:
1. pooled-major WR at 0bps,
2. Development 5bps PF,
3. pooled-major PF at 0bps,
4. pooled-major net at 0bps.

Research only. Live BBC unchanged.