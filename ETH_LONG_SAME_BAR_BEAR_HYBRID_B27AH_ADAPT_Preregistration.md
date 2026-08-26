# ETH LONG B27AH-Adapt — SAME_BAR_REJECTION + 4H BEAR Attribution — Preregistration

## Purpose
Adapt BTC B27AH to the ETH-specific regime finding from completed B27AG-Adapt.

BTC B27AH tested SAME_BAR + BULL because BTC B27AG pointed toward aligned BULL strength. ETH B27AG-Adapt showed the opposite historical concentration: LONG F75 outcomes were materially stronger in pre-signal 4H BEAR. Therefore the pair-specific adapted hypothesis is SAME_BAR_REJECTION + pre-signal 4H BEAR.

This is attribution/confirmation research only. BEAR was selected after B27AG and is therefore not independent unseen validation.

## Frozen inputs
- Trade cohort: exact B27AA-Adapt SAME_BAR_REJECTION executed entries.
- Fixed economics: exact persisted E10 + D60/F15 baseline.
- Hybrid economics: exact persisted B27AC-Adapt E10 profit-lock structural runner.
- Regime label: exact B27AG-Adapt `regime_at_signal` using causal SwingRegime defaults.
- no entry, F75, E10, F15, runner, fee, session, timeframe, or regime threshold changes.

## Primary comparison
Pooled major partitions:
1. SAME_BAR all regimes.
2. SAME_BAR + 4H BEAR — adapted primary attribution cell.
3. SAME_BAR + 4H BULL.
4. SAME_BAR + 4H SIDEWAYS.

For each report N, WR, PF, expectancy/trade, total net for fixed and hybrid economics.

## Partition transparency
Show BEAR-only external, development, and reference_validation separately. Small cells remain visible.

## Readout
Historical concentration is tagged `ETH_LONG_B27AH_ADAPT_BEAR_CONCENTRATION_OBSERVED` only if pooled-major BEAR has:
- fixed expectancy > all-regime fixed expectancy;
- fixed PF > all-regime fixed PF;
- hybrid expectancy > all-regime hybrid expectancy;
- hybrid PF > all-regime hybrid PF.

This status is descriptive only and cannot promote a production regime filter because BEAR was chosen after B27AG.

Research only; no live changes.