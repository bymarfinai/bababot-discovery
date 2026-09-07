# SOL LONG A42 Portfolio-State Anatomy — A44 Preregistration

## Purpose
A44 is a forensic causal-state anatomy experiment that continues directly from the A43 portfolio-integration rejection.

A42 `G_MAE145` remains a supported 15UTC recovery lane. A43 showed that adding the frozen A42 recovery to the frozen A24/A25 three-zone portfolio improved aggregate economics but degraded positive active-week rate in validation. A44 asks whether A42 recovery wins and fails arrive under measurably different **portfolio states already observable at the recovery entry**.

A44 is **not** an entry search, threshold search, clock search, geometry change, calendar/month filter, OOS retuning stage, or portfolio promotion test.

## Frozen sources
Source branch: `research/sol-long-structure-a1-run`.

Frozen baseline component ledger:
- `SOL_LONG_THREE_ZONE_BENCHMARK_A24_COMPONENTS.csv`
- A24/A25 component-trade conventions are preserved.

Frozen recovery ledger:
- `SOL_LONG_15UTC_A40_B2_GUARD_A42_TRADES.csv`
- only `role == CENTRAL`, `lane == G_MAE145`, and partitions `development`, `external`, `reference_validation` are studied.

Frozen A43 evidence:
- `SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_AUDIT.csv`
- `SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_RECONCILIATION.csv`

The 03UTC parent, 15UTC parent, 18UTC mature parent/REC_H2, A42 MAE threshold, E20/E10/E40 geometry, and all live Baba Bot code/configuration remain frozen.

## Strict causality rule
For a recovery entry at `reentry_ts`, portfolio-state features may use only frozen A24 component rows whose `exit_ts < reentry_ts` in the same partition.

No component that exits at or after `reentry_ts` may contribute to a causal feature.

A25 weekly convention is preserved exactly: weekly buckets use `W-MON` period semantics and active-period accounting is unchanged.

## Frozen causal portfolio-state features
For each A42 recovery row A44 computes, before entry:

1. `day_to_date_net_raw`
2. `day_to_date_net_stress`
3. `week_to_date_net_raw`
4. `week_to_date_net_stress`
5. `day_to_date_trades`
6. `week_to_date_trades`
7. `trailing_24h_net_raw`
8. `trailing_24h_net_stress`
9. `trailing_72h_net_raw`
10. `trailing_72h_net_stress`
11. `trailing_168h_net_raw`
12. `trailing_168h_net_stress`
13. `last3_component_mean_raw`
14. `last3_component_mean_stress`
15. `last5_component_mean_raw`
16. `last5_component_mean_stress`
17. `equity_drawdown_at_entry_raw`
18. `equity_drawdown_at_entry_stress`

All monetary features use the exact frozen component PnL units already used by A24/A25/A43.

## Outcome labels
The primary causal-anatomy outcome is frozen A42 recovery stress outcome:
- `WIN` if `recovery_pnl_5bps > 0`
- `FAIL` otherwise.

A44 also reconstructs the final A25-style baseline and +A42 day/week buckets to diagnose A43 hit-rate failures. These full-period fields are explicitly **non-causal outcome diagnostics** and may never be used as candidate input features:
- baseline final day/week PnL,
- +A42 final day/week PnL,
- positive→non-positive / non-positive→positive bucket flips.

## Development-first separator protocol
For each frozen causal feature:

1. Compute Development stress-WIN and stress-FAIL medians.
2. Compute the Development median gap (`WIN - FAIL`).
3. Normalize absolute gap by pooled winner/failer IQR when available to obtain an effect measure.
4. Record the same median-gap direction independently in CENTRAL external and CENTRAL reference-validation.

Because the frozen A42 lane is intentionally sparse, A44 is forensic evidence only. A feature may be labelled `replicated_directional` only when:
- Development has at least 2 stress FAIL rows and at least 5 stress WIN rows;
- external and reference-validation each have at least 2 stress FAIL rows and at least 3 stress WIN rows;
- Development effect is at least 0.50 (or infinite under a zero pooled IQR with non-zero gap);
- the sign of the Development gap is non-zero and matches both external and reference-validation.

No threshold is derived or tested in A44. No combination of features is tested in A44.

## Fixed outputs
A44 must persist:
- enriched per-recovery causal-state ledger;
- causal-feature separation table;
- A43 day/week flip diagnostic table;
- Markdown result and status.

The result must report:
- recovery counts and stress WR by partition;
- all positive→non-positive and non-positive→positive week flips caused by adding frozen A42;
- Development / external / reference-validation median gaps for any replicated-directional causal features;
- whether evidence is sufficient to justify a separately preregistered next guard experiment.

## Verdict labels
- `SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_SUPPORTED_FOR_NEXT_TEST`
- `SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_INCONCLUSIVE`
- `SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_RECONCILIATION_FAIL`

`SUPPORTED_FOR_NEXT_TEST` means only that at least one causal portfolio-state separator replicated directionally and may justify a new preregistered experiment. It does **not** promote A42 into the portfolio.

Research only. Live Baba Bot remains unchanged.
