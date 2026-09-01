# ETH B27DX — S6A Habitat-Specific Geometry Calibration — Preregistration

## Purpose
Test whether ETH's four structurally valid habitats require different static trade geometry rather than one global S3C medoid.

This hypothesis is motivated by S4/S5A: identical geometry/management produces materially different economics by clock, and BTC's mature B27DX lineage also ended with zone-specific operating treatment.

S6A does **not** introduce new parameter values. It reuses only the previously supported S3C joint family.

## Frozen structural layer
- LONG only;
- R300 / X360;
- clocks: **05:00, 09:00, 10:00, 16:00 UTC**;
- exact B27DX corrected causal grammar;
- same fee/notional, weekdays, partitions, and global one-position semantics.

## Frozen per-clock candidate universe
Only the 56 S3C family cells:
- entries: F85, F80, F75, F70;
- targets: E10, E15, E20, E25, E30, E35, E40;
- completed-close invalidations: F20, F15.

No new geometry value is allowed.

## Development-only habitat selection
For each clock independently, use **Development only** to define a quality-qualified cell.

A Development cell is eligible when:
- N >= 30;
- WR >= **65%**;
- PF >= **1.40**;
- expectancy >= **+$0.80/trade**;
- net > 0.

These thresholds require a material improvement in local quality relative to the S4 pooled baseline (WR 62.8%, PF 1.42, expectancy +$0.81) without directly selecting to the BTC benchmark.

### Local topology gate
Eligible cells are connected by the same 6-neighbor 3D adjacency used in S3C.

A clock has a selectable Development geometry only if its largest qualifying component has:
1. >=4 eligible cells;
2. >=2 distinct entry fractions;
3. >=2 distinct target extensions; and
4. both F20 and F15 represented.

### Deterministic per-clock representative
For each qualifying clock:
1. choose the largest eligible component;
2. select its coordinate medoid by minimum grid-Manhattan distance to component medians;
3. ties: higher entry first, lower target first, higher stop first.

No maximum-PF/WR cell is selected.

## Validation gate
The Development-selected representative is then evaluated unchanged in External and Reference Validation.

A clock validates only if **both** validation partitions independently have:
- N >= 15;
- WR >= 60%;
- PF >= 1.25;
- expectancy > 0;
- net > 0.

Validation results may not alter the selected geometry.

## Habitat-specific portfolio
Only clocks that pass the frozen validation gate enter the S6A portfolio, each using its Development-selected geometry.

Rebuild candidate paths and apply the exact S4 global one-position lock:
- earliest eligible entry while flat;
- exact-entry tie: latest execution-start timestamp, then execution-clock ascending;
- close/target exit availability remains causal as in S4.

Score 0 bps and 5 bps adverse execution.

## Final BTC benchmark diagnostic
Frozen BTC B27DX LONG benchmark:
- WR 71.9%;
- PF 2.22;
- expectancy +$1.26/trade;
- max loss streak 3.

S6A earns `BTC_QUALITY_SUPPORTED` only if Pooled Major 0 bps meets/exceeds WR, PF and expectancy, every major partition is positive with PF>1, and 5 bps pooled PF>=1/net>=0.

Frequency is reported but never overrides quality. The desired ~2 opportunities/week remains diagnostic.

## Evidence limitation
S3C validation partitions have already been inspected at aggregate level in prior stages. S6A is therefore exploratory calibration, not pristine unseen OOS confirmation. The Development-only selection rule is still enforced to prevent direct validation ranking.

## Decision states
- `ETH_S6A_HABITAT_GEOMETRY_BTC_QUALITY_SUPPORTED`
- `ETH_S6A_HABITAT_GEOMETRY_POSITIVE_BELOW_BTC`
- `ETH_S6A_NO_VALIDATED_HABITAT_GEOMETRY`

## Guardrails
- No new geometry values.
- No runner tuning in S6A.
- No validation-based representative changes.
- No leverage or live-code changes.
