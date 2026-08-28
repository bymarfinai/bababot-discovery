# BNB Session-Native London→New York LONG M4 Frozen F95 Validation — B27EP Preregistration

## Purpose
Validate exactly one development-selected entry rule from B27EO on the untouched candidate-selection partition: `reference_validation` only.

B27EP does not search, retune, rank, or introduce any alternative entry.

## Upstream structure
Reuse B27EM unchanged:
- BNBUSDT 5m.
- DST-aware London 08:00 local → New York 09:30 local reference range.
- `H = reference high`, `L = reference low`, `R = H-L`.
- NY execution 09:30 → 16:00 local.
- LONG K1 OPP0 and causal-leave state machine exactly as B27EM.
- Terminal semantics exactly as B27EM/B27EO: H2 is `high >= H`; opposite break is `close < L`; same-bar H2/opposite is ambiguous.

## Validation partition
Use only B27EM partition `reference_validation`:
- start: `2025-01-01`
- end exclusive: `2026-07-30`

Expected upstream integrity from B27EM:
- causal leaves: **45**
- upstream H2 arrivals: **35**
- upstream non-H2: **10**

Development, external, and August partitions must not be used to alter the rule or select a replacement.

## Frozen entry rule: E2_F95_RECLAIM
`F95 = L + 0.95 * R`.

After causal `leave_ts`, scan 5m bars forward causally.

For each completed bar before any terminal event:
1. require `low <= F95`, and
2. require `close > F95`.

The first bar satisfying both is the signal bar.

Entry fill is the **open of the next 5m bar** (`signal bar start + 5 minutes`).

The entry is eligible only if:
- no H2/opposite/ambiguous terminal occurred before the fill,
- the next 5m bar exists inside the NY execution window, and
- fill price is strictly inside the reference range: `L < entry_px < H`.

No alternative F-level, no first-bull-close fallback, no next-open fallback, no higher-low filter, and no DST filter may be introduced in B27EP.

## Metrics frozen before reveal
Primary:
- eligible F95 entries,
- H2 after entry,
- **H2-after-entry rate**.

Secondary diagnostics:
- eligible-entry rate out of 45 causal leaves,
- winner capture share out of 35 upstream H2 events,
- median leave→entry minutes,
- median entry→H2 minutes,
- median entry depth from H in R units,
- post-entry MAE in R units,
- Wilson 95% interval for H2-after-entry rate.

Context only:
- upstream structural H2 rate is `35/45 = 77.8%` before the frozen F95 entry condition.

## Confirmation target
The development observation was 20/21 = 95.2% H2-after-entry.

B27EP's predeclared headline target is:
- **F95 validation H2-after-entry rate >= 90.0%**.

Eligible N and the Wilson interval must be reported so a high percentage on a small sample is not treated as sufficient evidence by itself.

## Hard stop
B27EP ends after this frozen validation report.

Do not run TP/SL, PnL, fees, leverage, F90/F85 comparison, level retuning, SHORT, H3, breakout-retest, August reveal, or live integration automatically.