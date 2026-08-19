# BTC SR83 — All-Day Level Confidence Walk-Forward Result

**Verdict: REJECT_SR83_OOS_80_LEVEL_IDENTIFIER**

**Protocol:** frozen before result; research-only; live BBC untouched.

## Dataset

- BTCUSDT all WIB calendar days, 2020-01-01 through 2026-07-29
- Candidate levels frozen daily before first touch
- First-touch level events: **8,129**
- Resolved HOLD/BREAK events: **4,383**
- Outcomes: **2,351 HOLD / 2,032 BREAK / 3,724 ambiguous-touch-bar / 12 ambiguous-later-bar / 10 unresolved**
- Integrity violations: **0**

## Pseudo-OOS baseline

The annual expanding test years 2023–2026 contained **2,436 resolved levels**:
- HOLD **1,309**
- BREAK **1,127**
- unconditional HOLD rate **53.74%**
- Wilson 95% **51.75%–55.71%**

## High-confidence 80% search

Frozen annual model: `DecisionTreeClassifier(gini, max_depth=4, min_samples_leaf=50, random_state=20260819)`.

A training leaf could be labeled `HIGH_CONFIDENCE_HOLD` only when it contained at least 50 resolved historical levels and had empirical training HOLD rate >=80%.

**No qualifying leaf existed in any annual fold.** Therefore pseudo-OOS high-confidence coverage is zero; no test-year observation was allowed to be promoted by relaxing the preregistered standard.

| Train history | Test year | Test resolved N | Test baseline HOLD | Eligible >=80% training leaves | HC OOS N |
|---|---:|---:|---:|---:|---:|
| 2020–2022 | 2023 | 517 | 54.16% | **0** | 0 |
| 2020–2023 | 2024 | 746 | 54.16% | **0** | 0 |
| 2020–2024 | 2025 | 779 | 51.22% | **0** | 0 |
| 2020–2025 | 2026 through Jul29 | 394 | 57.36% | **0** | 0 |

## Conclusion

Within the preregistered information set—previous-day/7-day extrema, confirmed 1H swing levels, confluence, distance, prior visits, level age, pre-touch momentum/range/volume, EMA slope and ATR state—there is **no sufficiently supported 80% support/resistance state**.

This is stronger than a failed validation result: across four expanding historical training sets containing roughly 1,947 to 3,989 resolved events, the shallow supported tree could not form even one N>=50 leaf with >=80% historical HOLD reliability.

No deeper tree, smaller leaf, lower confidence threshold, support-only/resistance-only, source-family, year/hour, reaction-distance or horizon rescue is authorized on this dataset.

Historical level reliability is not a guarantee of future behavior and this study does not measure trade PnL.
