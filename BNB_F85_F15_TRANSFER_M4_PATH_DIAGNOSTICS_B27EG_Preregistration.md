# BNB F85/F15 Transfer — M4 Path Diagnostics — B27EG

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Diagnose why the exact frozen BTC signal structure transferred to BNB with high structural H2 hit rates, while the frozen BTC economic exits failed in B27EF.

This milestone is diagnostic only. It MUST NOT tune entries, clocks, F-levels, stops, targets, runners, portfolio priority, or any BNB-specific trading rule.

Primary contradiction to explain:
- ALT_0330 LONG: high structural H2 support in B27EE, but negative economics in B27EF.
- RAW_0530 LONG: high structural H2 support in B27EE, but negative economics in B27EF.
- SHORT_2000 is retained only as a comparison/control because it remained positive in B27EF.

## Frozen universe
- Branch: `bnb-transfer-b27ed-b27ef`.
- Instrument: Binance USD-M BNBUSDT perpetual.
- Raw event clock: 5m.
- Historical span and partitions remain exactly those frozen in B27ED/B27EE/B27EF.
- Candidate identity and geometry must reproduce B27EF exactly.
- Portfolio acceptance/rejection must reproduce B27EF exactly.
- Primary scoring universe: accepted trades in pooled-major partitions (`external`, `development`, `reference_validation`).
- Sources: `ALT_0330`, `RAW_0530`, `SHORT_2000`.

## Path horizon
For diagnostics, price path is observed from the frozen next-open entry through the frozen execution-window end, **even if B27EF exited earlier**. This is intentionally counterfactual path observation only; it does not alter realized B27EF PnL.

No future path information may be used to redefine entry eligibility or historical B27EF outcomes.

## Structural-event join
Each B27EF candidate must be joined back to the exact B27EE candidate using frozen identity:
`partition | side | source | entry_ts`.

Persist B27EE structural outcome (`H2`, `OPPOSITE_BREAK`, `NO_H2_BY_END`, `AMBIGUOUS`) and H2 timestamp when available.

## Diagnostic measurements
All distances are normalized by the frozen reference range `R`.

For LONG:
- full-window MFE_R = `(max high after entry - entry) / R`;
- full-window MAE_R = `(entry - min low after entry) / R`;
- pre-H2 MFE_R and MAE_R when H2 occurs;
- post-H2 extension_R = `(max high from H2 through execution end - H) / R`;
- whether H2 is followed by E10, E20, E30, E50 (`H + xR`) before execution end;
- execution-end return_R = `(execution-end open - entry) / R`.

For SHORT, use the exact mirrored definitions around L:
- MFE_R = `(entry - min low) / R`;
- MAE_R = `(max high - entry) / R`;
- post-H2 extension_R = `(L - min low from H2 onward) / R`;
- E10/E20/E30/E50 are `L - xR`;
- execution-end return_R = `(entry - execution-end open) / R`.

## Winner/loser cohorts
Realized B27EF economic label is frozen:
- WIN: `pnl > 0`;
- LOSS: `pnl <= 0`.

Report by source and by WIN/LOSS cohort:
- N;
- structural H2 rate;
- median and p25/p75 full-window MFE_R;
- median and p25/p75 full-window MAE_R;
- median pre-H2 MAE_R for H2 trades;
- median post-H2 extension_R;
- E10/E20/E30/E50 reach rates after H2;
- median execution-end return_R.

Also explicitly report:
1. fraction of B27EF economic losers that nevertheless achieved structural H2;
2. among H2 trades, fraction that reached E10/E20/E30/E50;
3. among H2 economic losers, fraction that later reached E10/E20/E30/E50 after the frozen economic exit;
4. whether RAW_0530 losses are primarily pre-H2 failures, insufficient post-H2 extension, or runner giveback after favorable extension;
5. whether ALT_0330 losses are primarily inability to reach E20 after H2 versus outright structural failure.

## Diagnostic interpretation labels
B27EG may assign descriptive labels only; these labels do NOT authorize a new strategy:
- `STRUCTURE_FAILS_BEFORE_H2` when most losses never achieve H2.
- `H2_WITHOUT_EXTENSION` when losses commonly achieve H2 but rarely reach E20.
- `EXTENSION_THEN_GIVEBACK` when losses commonly reach E20 or better after entry/path but frozen realized economics still lose.
- `MIXED_PATH_FAILURE` when no single mechanism dominates.

No cutoff may be optimized. For narrative classification, “commonly/most” means >=60% of the relevant loss cohort; otherwise use `MIXED_PATH_FAILURE`.

## Mandatory audits
Abort before persistence if any fail:
1. B27EF status file exists and equals `B27EF_BNB_FROZEN_ECONOMICS_NOT_SUPPORTED`.
2. B27EF candidate IDs and accepted/blocked flags reproduce exactly.
3. B27EE join is one-to-one for all B27EF candidates.
4. Raw BNB 5m coverage remains >=99.5%.
5. No candidate, entry, exit, PnL, or portfolio arbitration is modified.
6. Path diagnostics use only the already-frozen entry-to-execution-end interval.
7. No parameter sweep, clock search, target search, or strategy gate is run.

## Output status
This milestone has no profitability PASS gate. Successful execution status is:
`B27EG_BNB_PATH_DIAGNOSTICS_COMPLETE`.

B27EG MUST stop after diagnosis. Any BNB-native payoff geometry or decision to discard LONG requires a separate, later preregistered milestone.