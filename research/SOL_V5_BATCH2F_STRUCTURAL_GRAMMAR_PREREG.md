# SOL V5 Batch 2F — Structural Transition Motif / Grammar PREREG

## Objective
Test whether the frozen V4 `HIGH_STATE` expansion habitat contains **repeatable, economically executable LONG structural grammars** at state onset when the preceding 5m price structure is represented as a discrete sequence rather than a dense feature vector or probability score.

Batch 2E found that HH/HL/LH/LL channels carried the largest aggregate importance, but the flattened sequence classifier did not produce a tradable LONG subset. Batch 2F therefore removes the classifier and asks a narrower question:

> Does an exact, repeated terminal structural grammar observed before HIGH_STATE transfer out-of-sample with positive LONG economics?

## Research boundary
- SOLUSDT Futures 5m.
- Same frozen V4 state detector and Batch 1 HIGH_STATE episode definition.
- Research/development years: 2020–2024.
- Nested OOS test years: 2022, 2023, 2024.
- `2025+ reference_validation` remains CLOSED.

## Causal sequence
For each HIGH_STATE onset at time `T`, use only the 24 completed 5m bars from `T-120m` through `T-5m`.
The HIGH_STATE candle itself and all future bars are excluded from motif construction.

## Structural alphabet
For each transition from bar `i-1` to bar `i`:
- `U` = high non-decreasing and low non-decreasing, with at least one strictly higher (`HH/HL` family);
- `D` = high non-increasing and low non-increasing, with at least one strictly lower (`LH/LL` family);
- `O` = strict outside bar: higher high and lower low;
- `I` = strict inside bar: lower high and higher low;
- `F` = remaining equal/tie configuration.

No return magnitude, hour, EMA, VWAP, Fib, RSI, model score, or future information is used in the grammar itself.

## Frozen motif
The live motif is the **last 4 structural transition tokens** immediately preceding HIGH_STATE onset.

Examples: `D-D-I-U`, `D-I-U-U`, `U-U-I-D`.

Motif length is fixed at 4. No motif-length sweep is allowed.

## Outcome statistics
For each training motif compute:
- support `N`;
- `UP_FIRST` rate from the frozen Batch 1 barrier label;
- mean fixed +60m net return after 0.15% round-trip cost;
- profit factor;
- win rate.

The fixed +60m outcome is a diagnostic only; no TP/SL/time-stop optimization is allowed.

## Empirical shrinkage
To reduce small-sample motif optimism, freeze prior strength = **40 observations**.
For each training fold:
- global training mean net return = `global_edge`;
- global training UP_FIRST rate = `global_up_rate`;
- shrunk motif edge = `(N * motif_edge + 40 * global_edge) / (N + 40)`;
- shrunk motif UP_FIRST = `(N * motif_up_rate + 40 * global_up_rate) / (N + 40)`.

No shrinkage-strength sweep.

## Frozen motif eligibility
A motif is LONG-eligible in a test fold only if, using training data only:
1. training support `N >= 30`;
2. shrunk mean +60m net return `> 0`;
3. shrunk UP_FIRST rate `> global training UP_FIRST rate`.

No ranking percentile, top-k motif selection, model family, hour filter, or post-hoc rescue.

## Nested walk-forward
Use the same causal OOS HIGH_STATE episodes as Batch 2D/2E:
- predict/trade 2022 from OOS HIGH_STATE episodes in 2021;
- predict/trade 2023 from 2021–2022;
- predict/trade 2024 from 2022–2023.

The eligible motif dictionary is rebuilt separately for each test year from allowed past years only.

## Execution diagnostic
For an eligible motif:
- LONG at HIGH_STATE `anchor_price` / state onset;
- exit at fixed +60m close;
- round-trip cost = 0.15%;
- $500 reference notional;
- no TP, SL, trailing, time-stop, scaling, or post-entry management.

## Baseline
All HIGH_STATE episodes in the same 2022–2024 test universe using identical +60m economics.

## Outputs
- all OOS motif assignments;
- training motif dictionary per fold;
- eligible motif table per fold;
- OOS selected trades;
- pooled and yearly economics;
- motif transfer audit;
- grammar frequency table;
- gate audit and frozen verdict.

## Frozen PASS gates
All must pass:
1. selected OOS N >= 100;
2. selected OOS UP_FIRST lift >= 1.20x versus all HIGH_STATE;
3. selected fixed +60m net expectancy > 0;
4. selected fixed +60m PF >= 1.10;
5. positive selected PnL in >=2 of 3 test years;
6. at least 2 distinct eligible motifs actually trade OOS;
7. pooled selected expectancy exceeds all-HIGH_STATE baseline expectancy.

## Stop rule
If Batch 2F fails, do not rescue it on 2022–2024 by sweeping motif length, support threshold, prior strength, token definitions, hours, exit horizon, TP, or SL. A failure means exact short structural grammar, as preregistered here, is insufficient as a ready-to-trade LONG selector even though structural transitions are informative diagnostically.
