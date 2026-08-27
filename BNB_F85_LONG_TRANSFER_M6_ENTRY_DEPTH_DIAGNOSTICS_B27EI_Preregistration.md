# BNB F85 LONG Transfer — M6 Entry Depth Diagnostics — B27EI

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
B27EH showed that taking profit at H2 raises LONG WR materially but still leaves negative expectancy and PF below 1.0. B27EI tests whether the frozen BTC-style BNB LONG entry is geometrically misplaced: too shallow / too close to H, with insufficient reward-to-H versus downside carried from the entry.

This milestone is **diagnostic only**. It does not change candidate identity, execute alternative trades, optimize a level, change F35, or claim a new strategy.

## Frozen sample
- Instrument: Binance USD-M BNBUSDT perpetual; raw 5m.
- Sources: ALT_0330 LONG and RAW_0530 LONG only.
- Primary sample: exact B27EF accepted pooled-major LONG set, expected N=106 = 55 ALT_0330 + 51 RAW_0530.
- Partitions: external, development, reference_validation; august remains diagnostic only.
- B27EG economic labels and structural H2 identity must join one-to-one.
- Existing entry remains exact F85 confirmation followed by next raw5m open with F35 < open < H.
- No SHORT logic is changed or analyzed beyond prerequisite integrity.

## Current-entry geometry diagnostics
For every frozen LONG trade compute using only already-frozen H/L/R and the raw 5m confirmation/entry bars:
- confirmation close depth: `(confirmation_close - L)/R`;
- next-open entry depth: `(entry_px - L)/R`;
- next-open premium versus F85: `(entry_px - F85)/R`;
- reward from actual entry to H: `(H - entry_px)/R`;
- nominal distance from actual entry to F35: `(entry_px - F35)/R`;
- nominal H2 reward/risk ratio: `(H-entry)/(entry-F35)`;
- confirmation-close to next-open gap in R.

Report these for ALL / B27EF WIN / B27EF LOSS and for structural H2 / non-H2 cohorts, by source and pooled LONG.

## Causal deeper-entry opportunity atlas
The diagnostic ladder is frozen before execution: **F80, F75, F70, F65**. These are not selected entry rules in B27EI.

For each frozen signal and each level `Fx = L + x*R`:
1. The hypothetical limit is considered placeable starting at the exact frozen `entry_ts` (the next-open moment after F85 confirmation).
2. Search forward only within the original execution window.
3. A fill opportunity exists at the first raw5m bar with `low <= Fx` while the level remains below H.
4. If the first fill-opportunity bar also has `high >= H`, mark `AMBIGUOUS_FILL_H2_SAME_BAR`; do not credit post-fill H2 because intrabar ordering is unknowable.
5. Otherwise, after a clean fill bar, classify whether a later raw5m bar reaches H (`high >= H`) before execution-window end.
6. Also measure post-fill MAE to window end and reward-to-H from the hypothetical fill price.
7. No stop, PnL, fee, runner, or target beyond H is simulated in this atlas.

Required per-level outputs by source, partition, and pooled-major:
- eligible signals;
- clean fill count and fill rate;
- ambiguous fill/H2 same-bar count;
- no-fill count;
- clean-fill later-H2 count and H2-after-fill rate;
- median minutes fill-to-H2;
- median reward-to-H in R;
- median post-fill MAE in R.

## Frozen interpretation labels
B27EI may label a deeper level `ENTRY_DEPTH_CANDIDATE` only as a **diagnostic candidate for a later preregistered economic test**, never as a selected strategy, if pooled-major all hold:
1. clean fills >= 30;
2. clean fill rate >= 30% of the 106 frozen accepted LONG signals;
3. H2-after-fill >= 75%;
4. ALT_0330 and RAW_0530 each have >=10 clean fills and H2-after-fill >=70%;
5. every major partition with >=5 clean fills has H2-after-fill >=65%;
6. median reward-to-H at fill is at least 0.20R.

If multiple levels satisfy this diagnostic label, B27EI reports all of them. It does **not** rank or select one by PnL because no economics are allowed in this milestone.

## Mandatory audits
Execution must abort before persistence if any fail:
1. B27EH status remains `B27EH_BNB_TWO_STAGE_ECONOMICS_NOT_SUPPORTED` and B27EG is complete.
2. Exact 106 accepted pooled-major LONG candidate IDs from B27EF are preserved.
3. Entry timestamps, entry prices, confirmation timestamps, H/L/R, F85 and F35 match frozen lineage.
4. Confirmation close is read from the exact raw5m confirmation bar; entry price matches exact raw5m entry-bar open.
5. Deeper-level search begins no earlier than frozen entry_ts.
6. Same-bar deeper-fill + H2 is ambiguous, never assumed favorable.
7. No alternative-entry PnL, stop tuning, filtering, or post-result parameter change is performed.
8. Raw BNB 5m coverage >=99.5%.
9. Outputs persist only to branch `bnb-transfer-b27ed-b27ef`; `main` is untouched.

**Research only. Stop after B27EI diagnostics. Any actual alternative entry must be a separate preregistered milestone.**