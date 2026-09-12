# BNB R4b — Stage D 2025 Final Full-Year OOS Preregistration

## Final information firewall

- Open **2025 full-year only** as final OOS.
- Only Stage-C components with verdict `ECONOMIC_PLATEAU_PERSISTS` are eligible.
- Their WIB hour, character rule, and exact frozen 2022 member cells are immutable.
- No 2025 reselection, best-coordinate substitution, center shift, member deletion/addition, feature tuning, TP/SL tuning, SHORT search, weekday filter, or gate relaxation.
- **2026 remains CLOSED** and is not used anywhere in Stage D.

## Per-cell 2025 economic viability

A frozen cell is economically viable in 2025 when:

- N `>= 50`
- WR `>= 52%`
- Net `> 0`
- expectancy `> 0`
- PF `>= 1.15`
- DD `<= min($160, 1.50 × 2022 DD + $20)`

Loss streak is a risk-clustering diagnostic only, warned when `LS > max(12, 2022 LS + 4)`.

A viable cell is separately flagged strict-stable vs 2022 when WR deterioration is no worse than 5pp, expectancy retention is at least 60%, and PF retention is at least 70%. Strict retention is diagnostic; final robustness is a plateau-level judgment.

## Final component verdict

For each frozen persistent plateau independently:

- `FINAL_OOS_PLATEAU_PASS` if viable fraction `>= 50%`, median expectancy `> 0`, and median PF `>= 1.15`;
- `PARTIAL_FINAL_OOS_PERSISTENCE` if at least 2 cells are viable, or if median expectancy `> 0` and median PF `> 1.00`;
- otherwise `FINAL_OOS_PLATEAU_FAIL`.

A BNB character may be called **final robust under R4b** only when its entire frozen component receives `FINAL_OOS_PLATEAU_PASS`. The result may contain zero, one, or multiple final robust plateaus.

## Outputs

Persist:

- complete 2025 member-cell results for every Stage-C survivor;
- final component verdict table;
- final robust plateau table;
- scientific final-OOS report and status.

The sum of per-cell Net is descriptive only because timing variants overlap; it is not portfolio PnL.

Research/shadow only. No claim of guaranteed live profitability.