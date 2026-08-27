# BNB Session-Native London→New York LONG M2 Native Retracement Depth — B27EN Preregistration

## Purpose

B27EN is the first post-B27EM entry-discovery milestone. It asks one structural question only:

> After a causal K1 high leave, how deep does BNB naturally retrace before H2, and does the inherited F85 level (`L + 0.85R`) sit inside that native geometry?

This stage does **not** create a trading setup. It does not test TP/SL, PnL, fees, position sizing, SHORT, session-clock alternatives, DST filters, or live integration.

## Frozen parent

- Parent milestone: `B27EM_BNB_LONDON_NY_LONG_STRUCTURE_COMPLETE`
- Parent branch/head: `bnb-session-native-london-ny` / `2b26c30ae3268c707c958b165dfaa218db008724`
- Target: `BNBUSDT`
- Bars: raw 5m
- Session clock remains DST-aware and unchanged:
  - reference: `08:00 Europe/London -> 09:30 America/New_York`
  - observation: `09:30 -> 16:00 America/New_York`
- K1 / OPP0 / causal-leave / H2 definitions are inherited unchanged from B27EM.

## Discovery partition only

B27EN uses **development only**:

- `2022-01-01T00:00:00Z <= bar time < 2025-01-01T00:00:00Z`

`external`, `reference_validation`, and `august` are not used to select or rank retracement levels. They remain untouched for later validation milestones.

## Unit of analysis

One row per B27EM development event satisfying:

1. qualified High K1 OPP0,
2. causal leave exists.

B27EM reported 97 such development leaves. B27EN must reproduce that count before geometry is accepted.

## Causal measurement window

For each causal leave:

- start = `leave_ts` (the first timestamp at which the completed leave candle is knowable),
- end = start of the terminal candle for `H2_ARRIVAL`, `OPPOSITE_BREAK_BEFORE_H2`, or an ambiguous terminal,
- end = New York close for `NO_H2_BY_END`.

The terminal candle itself is excluded from depth measurement. This deliberately avoids assuming intrabar ordering when an entry level and H2/opposite break could occur in the same 5m candle.

## Native depth definition

Let the frozen reference range be:

- `H` = London->NY reference high,
- `L` = London->NY reference low,
- `R = H - L`.

For the pre-terminal path:

- `pre_terminal_low` = minimum low after `leave_ts` and strictly before the terminal candle,
- if no full 5m bar exists before terminal, set `pre_terminal_low = H`,
- `depth_from_H_R = max(0, (H - pre_terminal_low) / R)`,
- `lowest_level_fraction = (pre_terminal_low - L) / R`.

Thus inherited `F85 = L + 0.85R` corresponds to a retracement depth of `0.15R` from H.

## Descriptive outputs

B27EN will report, on development only:

1. winner (`H2_ARRIVAL`) depth quantiles: P10, P25, P50, P75, P85, P90, P95,
2. non-H2 depth quantiles separately,
3. predeclared level-reach table for:
   - F95, F90, F85, F80, F75, F70, F65, F60, F55, F50, F45, F40, F35,
4. for each level:
   - all-event causal reach count/rate,
   - H2 causal reach count and share of all H2 winners captured,
   - non-H2 causal reach count,
   - structural H2 share among events that causally reached the level,
   - median minutes from causal leave to first causal level touch.

These are **structural diagnostics**, not win rates or economics.

## No optimization rule

The level grid is fixed before results are revealed. B27EN will not tune a threshold or promote an entry rule automatically.

The output may identify a BNB-native candidate band, but any chosen level must be frozen only after reviewing this development-only result. That frozen choice, if any, requires a separate later validation milestone on untouched data.

## Integrity gates

B27EN fails if any of the following occurs:

- development causal-leave count does not reproduce B27EM's 97,
- a non-development row enters the analysis table,
- any event has `R <= 0`,
- any measurement window starts before `leave_ts`,
- any terminal candle is included in the pre-terminal depth window,
- any result is labeled as trading WR/PnL.

## Stop condition

STOP after development-only native depth geometry is persisted. Do not run confirmation logic, entry execution, TP/SL, economics, validation, SHORT, or live integration automatically.
