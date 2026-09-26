# SOL Indicator Relationship Discovery — Stage 2 Target Definition

**Status:** PREREGISTERED / FROZEN BEFORE INDICATOR RELATIONSHIP RESULTS  
**Scope:** SOLUSDT USD-M perpetual  
**Purpose:** define outcome labels before testing volume / breakout / taker / OI / funding relationships.  
**Live trading:** untouched.

## 1. Research clock

### Raw clock
- Canonical raw resolution: **5 minutes**.
- Raw 5m bars are used for:
  - exact next-open anchor;
  - first-touch ordering;
  - MFE / MAE;
  - lead-lag features later.

### Primary decision grid
- One decision timestamp every **15 minutes**: minute `00/15/30/45`.
- A decision at time `t` may use only information fully known at or before `t`.
- The completed 15m bar ending at `t` is therefore observable.
- Features from higher timeframes may only be forward-filled after their candle has fully completed.

### Entry anchor
- Entry reference = **first raw 5m open at decision time `t`**, after the 15m decision bar has completed.
- No same-signal-bar close entry is allowed.
- This anchor is used only to measure forward outcomes in Stages 2–6; it is not yet a trading rule.

## 2. Frozen historical partitions

- **Development:** 2023-01-01 00:00 UTC to 2025-01-01 00:00 UTC.
- **Validation 2025:** 2025-01-01 00:00 UTC to 2026-01-01 00:00 UTC.
- **Validation 2026:** 2026-01-01 00:00 UTC to the final completed data timestamp available when the dataset is frozen.

Rules:
- Thresholds, bins, interaction definitions, and state definitions may be learned only on Development.
- 2025 and 2026 are validation only.
- No post-hoc threshold rescue from validation data.

## 3. Primary economic-direction target

Primary target is a **gross ±1.00% symmetric first-touch race within 4 hours** from the entry anchor.

Let:
- `E` = entry reference price;
- upper barrier = `E * 1.01`;
- lower barrier = `E * 0.99`.

Scan subsequent raw 5m OHLC bars from entry time through 4 hours.

### `target_1pct_4h`
- `LONG`: upper +1.00% barrier is touched strictly before lower -1.00%.
- `SHORT`: lower -1.00% barrier is touched strictly before upper +1.00%.
- `NONE`: neither barrier is touched within 4 hours.
- `AMBIGUOUS`: both barriers lie inside the same 5m bar before either had previously been touched.

Ambiguity handling:
- `AMBIGUOUS` is never credited as a directional win.
- In later LONG testing it counts as adverse/failure.
- In later SHORT testing it also counts as adverse/failure.
- This preserves the repository's conservative same-bar convention.

Derived binary labels:
- `long_win_1pct_4h = 1` only for `LONG`; otherwise 0.
- `short_win_1pct_4h = 1` only for `SHORT`; otherwise 0.

The primary target is frozen before observing indicator relationships.

## 4. Secondary first-touch horizons

Using exactly the same entry anchor and ±1.00% barriers, generate:

- `target_1pct_1h`
- `target_1pct_2h`
- `target_1pct_4h` **PRIMARY**
- `target_1pct_8h`

Each uses the same four-state label:
`LONG / SHORT / NONE / AMBIGUOUS`.

These horizons are diagnostics, not independent opportunities to select whichever looks best after results.

## 5. Threshold-free forward-return targets

From the same entry anchor, calculate:

- `fwd_ret_1h`
- `fwd_ret_2h`
- `fwd_ret_4h`
- `fwd_ret_8h`

Formula:

`fwd_ret_H = future_close_at_H / E - 1`

The future close is the last completed raw 5m close ending exactly at the horizon boundary.

These continuous returns are required so Stage 3 does not rely only on an arbitrary ±1% threshold.

## 6. Excursion targets

For each horizon `H in {1h, 2h, 4h, 8h}`:

- `max_up_H = max(high / E - 1)`
- `max_down_H = min(low / E - 1)`
- `mfe_long_H = max_up_H`
- `mae_long_H = abs(min(0, max_down_H))`
- `mfe_short_H = abs(min(0, max_down_H))`
- `mae_short_H = max(0, max_up_H)`

Also record:
- `time_to_up_1pct_min`
- `time_to_down_1pct_min`

If a barrier is never reached inside 8h, its time-to-target is null.

## 7. Regime-conditioned outcome fields

The outcome table itself does not use regime to define success.

Later feature tables may join the latest causally-known Regime Detector state at decision time:
- `BULL`
- `BEAR`
- `SIDEWAYS`
- `TRANSITION`

This allows Stage 3–6 to ask whether the same indicator state has different outcomes by regime without changing target definitions.

## 8. Outcome-table schema

Minimum label table:

- `decision_time`
- `entry_time`
- `entry_price`
- `target_1pct_1h`
- `target_1pct_2h`
- `target_1pct_4h`
- `target_1pct_8h`
- `long_win_1pct_4h`
- `short_win_1pct_4h`
- `fwd_ret_1h`
- `fwd_ret_2h`
- `fwd_ret_4h`
- `fwd_ret_8h`
- `max_up_1h`, `max_down_1h`
- `max_up_2h`, `max_down_2h`
- `max_up_4h`, `max_down_4h`
- `max_up_8h`, `max_down_8h`
- `time_to_up_1pct_min`
- `time_to_down_1pct_min`
- `future_data_complete_1h`
- `future_data_complete_2h`
- `future_data_complete_4h`
- `future_data_complete_8h`

## 9. Missing-data and truncation rules

- A horizon label is null if the required future raw 5m path is incomplete.
- No price forward-fill across missing future bars.
- A row near the dataset end is not scored for horizons that extend beyond the frozen dataset.
- Feature missingness and target missingness must be reported separately.
- Outcome construction is performed in a separate table from indicator-feature construction until feature definitions are frozen.

## 10. Economics are deliberately separate

The Stage 2 barrier is **gross ±1.00% price movement**.

Trading economics such as:
- 0.15% modeled round-trip cost;
- slippage;
- actual net RR;
- one-position-at-a-time restrictions;
- cooldown;
- trade-frequency constraints;

are not used to redefine the Stage 2 outcome.

Those belong to Signal Rule Discovery / economic validation later.

For reference only, gross ±1% with a 0.15% round-trip cost is not net-symmetric; Stage 7 must evaluate net expectancy explicitly rather than interpreting raw barrier WR as PnL.

## 11. Anti-overfitting rules

1. The primary label remains `target_1pct_4h`.
2. 1h / 2h / 8h may explain timing but cannot replace 4h merely because they produce higher WR.
3. No TP/SL sweep is allowed during Stage 3 single-indicator discovery.
4. No indicator threshold may be chosen from 2025 or 2026.
5. Overlapping 15m observations are permitted for anatomy, but inferential tests must account for serial dependence using chronological blocks / clustered or block-bootstrap uncertainty.
6. Final trading-signal evaluation later must enforce non-overlapping executable positions.

## 12. Stage 2 completion criterion

Stage 2 is complete when:
- the above target definitions are frozen;
- target generation can be implemented deterministically from raw SOLUSDT 5m OHLC;
- no volume, taker, OI, funding, breakout, or regime result has been used to choose the target.

**Stage 2 verdict: TARGET_DEFINITION_FROZEN**
