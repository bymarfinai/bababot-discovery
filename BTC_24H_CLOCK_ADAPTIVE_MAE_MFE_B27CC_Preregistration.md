# B27CC — BTC 24H Clock-Adaptive Pre-Break SHORT MAE/MFE Anatomy — Preregistration

## Purpose
B27CA supported a clock-adaptive pre-break SHORT entry geometry, while B27CB showed that stops defined as 1R/2R where `LOCAL_R = entry - previous-4H Low` were far too tight economically.

B27CC diagnoses the price path after the exact frozen B27CA entries. It does NOT search or promote a stop/TP.

Research only. No live BBC change.

## Frozen entry cohort
Reuse only the exact B27CA development-selected clock rules:
- 00-04 UTC: F05
- 04-08 UTC: F05
- 08-12 UTC: F10
- 12-16 UTC: F05
- 16-20 UTC: F05
- 20-00 UTC: F05

Use the persisted B27CA candidate and event files. Exact filled-entry identity must reproduce:
- external 250
- development 380
- reference_validation 177
- pooled major 807
- pooled OOS external+reference_validation 427.

No entry fraction, clock, regime, weekday, EMA, ATR, volume, or candle filter may be changed.

## Structural labels
For each frozen filled entry:
- `WINNER_STRUCTURAL` = B27CA `eventual_low_break_after_fill == True`;
- `FAILURE_STRUCTURAL` = otherwise.

This is not trading WR.

## Evaluation window
Use BTCUSDT raw 5m.

The fill candle itself has ambiguous intrabar ordering. Therefore report it separately as `fill_bar_adverse_span` but do NOT include it in the primary causal MAE/MFE.

Primary causal window starts at the NEXT raw 5m candle after the fill candle.

Window termination:
- structural winner: include bars through the first Low-break candle (`close < L`) and stop at its completion;
- structural failure with first opposite boundary break after fill: include bars through that High-break candle (`close > H`) and stop at its completion;
- otherwise stop at the end of the same 4H observation block.

No bar after the structural terminal may affect the anatomy.

## Frozen excursion definitions
Let:
- `entry` = exact B27CA adaptive fill price;
- `R4 = H - L` = immediately previous completed 4H range;
- `LOCAL_R = entry - L`.

For SHORT:
- `MAE_px = max(0, max(high after fill) - entry)`;
- `MFE_px = max(0, entry - min(low after fill))`.

Normalize both as:
- fraction of `R4`;
- multiples of `LOCAL_R`.

Also report `fill_bar_adverse_span = max(0, fill_bar_high - entry)` in both normalizations.

## Required reporting
Report separately for structural winners and failures:
- N;
- MAE P50 / P75 / P90 as %R4 and LOCAL_R multiples;
- MFE P50 / P75 / P90 as %R4 and LOCAL_R multiples;
- fill-bar adverse P50 / P75 / P90 in LOCAL_R;
- proportion whose causal MAE exceeds 1R / 2R / 3R / 4R;
- median minutes fill -> terminal.

Required scopes:
- external, development, reference_validation;
- pooled OOS;
- pooled major;
- every 4H clock block on pooled major;
- every 4H clock block on pooled OOS.

Persist one row per frozen B27CA filled entry with exact timestamps and all excursion fields.

## Interpretation discipline
B27CC is anatomy only. WR/PF/PnL/expectancy are not applicable.

`B27CC_CLOCK_EXCURSION_INFORMATIVE` may be used only if:
1. exact entry identity passes;
2. every clock has >=20 pooled-major entries;
3. structural winners have valid MAE distributions in every clock;
4. at least one clock shows winner MAE P75 >2.0 LOCAL_R OR the six clock winner MAE-P75 values span >=1.0 LOCAL_R from minimum to maximum.

Otherwise use `B27CC_CLOCK_EXCURSION_NOT_INFORMATIVE`.

An informative result only permits a separately preregistered risk-geometry experiment. It does not authorize choosing a stop post hoc inside B27CC.