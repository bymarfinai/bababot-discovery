# SOL DD15 — Frozen Shortlist Validation Preregistration

## Purpose

Validate the seven frozen rank-1 hourly SOLUSDT LONG structures produced by the completed DD15 re-score, without reopening discovery or changing rule, lookback, hold, anchor set, fee, partitions, or thresholds after OOS exposure.

Research/shadow only. No live promotion or profit guarantee.

## Frozen shortlist

| Hour | UTC | WIB | Character | Lookback | Hold | Provenance |
|---|---|---|---|---:|---:|---|
| H15 | 15:00-16:00 | 22:00-23:00 | EFF_HIGH__RANGE_LOW | 240m | 960m | original |
| H17 | 17:00-18:00 | 00:00-01:00 | EFF_LOW__RANGE_HIGH | 30m | 720m | rescued |
| H18 | 18:00-19:00 | 01:00-02:00 | RV_HIGH__RANGE_MID | 120m | 720m | rescued |
| H20 | 20:00-21:00 | 03:00-04:00 | DRIVE_UP__STR_B80_100 | 360m | 960m | rescued |
| H21 | 21:00-22:00 | 04:00-05:00 | DRIVE_UP__RV_HIGH | 360m | 960m | rescued |
| H22 | 22:00-23:00 | 05:00-06:00 | EFF_LOW__EXT_MID | 240m | 360m | original |
| H23 | 23:00-00:00 | 06:00-07:00 | DRIVE_DOWN__STR_B80_100 | 15m | 120m | original |

Only rank 1 from each passing hour is eligible. Secondary H17/H22 variants are supporting evidence and may not replace a failed candidate.

## OOS integrity

- H15, H22, and H23 were already evaluated in the prior frozen-winner OOS run. Their prior OOS observations are not fresh and their locked failure evidence must be preserved.
- H17, H18, H20, and H21 have not previously been promoted into the formal OOS validator. External and Reference Validation are opened for them only after this preregistration.
- No candidate is replaced, narrowed to a favorable anchor, or tuned after inspection.

## Frozen mechanics and partitions

- SOLUSDT Binance USD-M Futures raw 5m; weekdays only; LONG only.
- Four quarter-hour anchors inside the frozen UTC hour.
- Exact 5m-open entry; exact-open exit after the frozen hold.
- Fixed $500 notional; $0.75 round-trip fee.
- Causal percentile normalization: trailing 60 same-anchor observations; minimum 40 prior.
- External: [2020-01-01, 2022-01-01).
- Development provenance: [2022-01-01, 2025-01-01).
- Reference Validation: [2025-01-01, 2026-07-30).
- August 2026 remains excluded.

## Frozen validation gates

### Partition support

External and Reference Validation must each independently satisfy the original support gate:

- N >= 40;
- WR >= 52%;
- net and expectancy > 0;
- PF >= 1.05;
- max DD <= $125;
- max loss streak <= 10.

### Combined OOS pooled gate

- N >= 160;
- WR > 55%;
- net > 0;
- expectancy >= $0.50/trade;
- PF >= 1.20;
- max DD / net profit <= 15%;
- max loss streak <= 8.

The DD ratio replaces only the former combined pooled hard-DD ceiling. No other threshold changes.

### Exact-anchor / anchor-local gate

For the combined chronological OOS observations, each of the four frozen quarter-hour anchors is evaluated under the unchanged partition-support thresholds. At least three anchors must be evaluable (N >= 40) and at least three must be supportive. No favorable-anchor subset may become a replacement strategy.

### All-era gate

Development 2022/2023/2024 provenance must still reconcile to the DD15 audit. External and Reference Validation must both pass their partition gates. Per-year OOS statistics are diagnostic and cannot create a post-hoc rescue.

## Verdicts

- VALIDATED: Development provenance reconciles and every formal OOS partition, pooled, and anchor-local gate passes.
- FAILED: at least one non-sample economic, risk, consistency, or anchor gate fails.
- INCONCLUSIVE: the only failures are insufficient sample/evaluable-anchor counts.
- RECONCILIATION_FAIL: reproduced Development statistics or candidate identity do not match the frozen audit.

Stop after this run. Do not open new hours, rules, Fibonacci coordinates, thresholds, exits, or candidate substitutions.
