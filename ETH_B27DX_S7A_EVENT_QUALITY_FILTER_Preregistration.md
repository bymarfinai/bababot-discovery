# ETH B27DX — S7A Native Event-Quality Filter Discovery — Preregistration

## Purpose
Test whether the missing BTC-class quality on ETH comes from treating every causally valid B27DX event as equally tradeable.

BTC's mature lineage used causal zone-quality filters such as TOUCH_FIRST_HALF and RANGE_COMPLETED_SECOND_HALF. ETH has not yet calibrated an equivalent event-quality layer.

S7A freezes ETH structure and fixed trade geometry, and changes **pre-entry causal event filters only**.

## Frozen ETH signal / trade layer
- LONG only;
- R300 reference / X360 execution;
- clocks 05:00, 09:00, 10:00, 16:00 UTC;
- F75 entry;
- E25 fixed target;
- F20 completed-close invalidation;
- exact B27DX causal grammar;
- same notional, fee, partitions, weekdays, and S4 global one-position lock.

No runner is used in S7A.

## Causal features
All features must be known no later than the candidate entry bar.

### 1. Reference range completion timing
Reconstruct the first occurrence of final H and final L inside the completed 300-minute reference window.

`range_completion_ts = max(first_H_ts, first_L_ts)`

- `RANGE_COMPLETED_FIRST_HALF`: completion elapsed < 150 minutes from reference start.
- `RANGE_COMPLETED_SECOND_HALF`: completion elapsed >= 150 minutes.

### 2. K1 timing
`k1_elapsed = k1_start - execution_start`

- `K1_FIRST_HALF`: <= 180 minutes.
- `K1_SECOND_HALF`: > 180 minutes.

### 3. Retrace fill timing
`fill_elapsed = entry_fill_bar_start - execution_start`

- `FILL_FIRST_HALF`: <= 180 minutes.
- `FILL_SECOND_HALF`: > 180 minutes.

The half-window thresholds are structural halves of ETH's frozen R300/X360 lifecycle; they are not optimized numeric cutoffs.

## Preregistered filter set
Per clock test exactly:
1. BASE
2. RANGE_COMPLETED_FIRST_HALF
3. RANGE_COMPLETED_SECOND_HALF
4. K1_FIRST_HALF
5. K1_SECOND_HALF
6. FILL_FIRST_HALF
7. FILL_SECOND_HALF
8. K1_FIRST_HALF__RANGE_COMPLETED_SECOND_HALF
9. FILL_FIRST_HALF__RANGE_COMPLETED_SECOND_HALF

No additional combination may be added after results are seen.

## Development promotion gate
A non-BASE filter is Development-promotable for a clock only if:
- accepted/trade N >= 20 before cross-clock portfolio locking;
- raw candidate retention >= 50%;
- WR >= **75%**;
- PF >= **1.50**;
- expectancy >= **+$0.80/trade**;
- net > 0.

If multiple filters pass, selection is deterministic and **not performance-maximizing**:
1. fewer filter components first;
2. higher raw retention;
3. preregistered filter order.

If none pass, the clock is not promoted.

## Historical replication gate
A Development-selected filter is historically replicated only if External and Reference Validation each independently have:
- N >= 10;
- raw retention >= 40%;
- WR >= 70%;
- PF >= 1.20;
- expectancy > 0;
- net > 0.

Validation may accept/reject the Development choice but may not change it.

## Promoted portfolio
Combine only historically replicated clock/filter pairs and rerun the exact global one-position lock.

Score:
- 0 bps primary;
- 5 bps adverse execution stress using S4 fixed-exit conventions.

## Final quality benchmark
BTC B27DX LONG benchmark:
- WR 71.9%;
- PF 2.22;
- expectancy +$1.26/trade;
- max loss streak 3.

S7A BTC-quality support requires Pooled Major 0 bps to meet/exceed WR, PF, and expectancy; every major partition must have positive net/PF>1; and 5 bps pooled PF>=1/net>=0.

Frequency remains diagnostic. Desired ETH cadence is ~2 opportunities/week, but quality cannot be traded away to hit frequency.

## Evidence label
Prior ETH histories have been inspected in earlier stages. S7A is exploratory causal-filter calibration, not pristine unseen OOS confirmation.

## Decision states
- `ETH_S7A_FILTER_PORTFOLIO_BTC_QUALITY_SUPPORTED`
- `ETH_S7A_FILTERS_REPLICATED_BELOW_BTC`
- `ETH_S7A_DEV_FILTERS_NOT_REPLICATED`
- `ETH_S7A_NO_DEV_FILTER`
- `ETH_S7A_CAUSAL_AUDIT_FAILED`

## Guardrails
- No filter cutoff sweep.
- No new entry/target/stop/lifecycle/clock values.
- No runner/leverage tuning.
- No validation-based reselection.
- No live BBC changes.
