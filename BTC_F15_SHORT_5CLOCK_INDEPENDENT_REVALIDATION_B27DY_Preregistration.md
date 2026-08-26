# B27DY — Five Additional F15 SHORT Clocks Independent Revalidation — Preregistration

## Purpose
Re-validate the five additional B27DR SHORT clocks independently using the same historical robustness philosophy applied to SHORT20 before any live integration.

This is a frozen-rule validation. It is not a new clock search and no clock may be tuned after results are observed.

## Frozen candidates
The five additional clocks are fixed before scoring:

- `SHORT_0000` — reference 00:00 UTC
- `SHORT_0300` — reference 03:00 UTC
- `SHORT_0330` — reference 03:30 UTC
- `SHORT_0430` — reference 04:30 UTC
- `SHORT_2100` — reference 21:00 UTC

Existing `SHORT_2000` is the already-validated control and is not re-selected by B27DY.

## Frozen SHORT structure
Identical to B27DR/B27DU SHORT20:

- BTCUSDT Binance USD-M perpetual raw 5m data.
- Reference duration 5h30m; execution duration 6h30m immediately following reference.
- Skip Saturday/Sunday execution starts.
- Frozen prior-range H/L.
- First Low pressure visit with High visits=0.
- Causal leave from the Low episode.
- First F15 touch before Low H2 / opposite High break.
- Same touch bar must close below F15.
- Entry only at the next raw 5m open.
- Entry geometry: `L < entry < F65`.
- `F15 = L + 0.15R`.
- `F65 = L + 0.65R`.
- `E20_DOWN = L - 0.20R`.
- TP at exact E20_DOWN.
- Invalidation only on completed raw 5m close above F65.
- Time exit at execution-window-end next/open price per frozen B27DR semantics.
- $500 illustrative notional; $0.40 round-trip fee.
- No EMA/ATR/volume/body/wick/regime filter.

## Individual chronological stability gate
Use the same fixed chronological windows as B27DU:

- W1: 2020-01-01 to 2021-07-01
- W2: 2021-07-01 to 2023-01-01
- W3: 2023-01-01 to 2024-07-01
- W4: 2024-07-01 to 2026-01-01
- W5_YTD: 2026-01-01 to 2027-01-01, diagnostic only

A completed window passes iff:
- N >= 8
- WR >= 60%
- PF >= 1.20
- net > 0

Chronological stability is SUPPORTED iff:
- at least 3 of 4 completed windows pass; and
- no completed window with a defined PF has PF < 0.80.

Calendar-year metrics are diagnostic only and cannot be used to select/tune a clock.

## Independent portfolio compatibility gate
Each additional clock is first evaluated independently against the frozen pre-B27DX B27DQ LONG stream using the same global one-BTC-position chronological lock.

Portfolio compatibility is SUPPORTED iff:
- at least 3 of 4 completed windows have positive LONG+clock net delta versus LONG-only;
- pooled-major accepted LONG displacement = 0; and
- pooled-major LONG+clock net exceeds LONG-only net.

This is a pre-B27DX compatibility benchmark only. Final live authorization still requires repeating portfolio parity after B27DX causal LONG correction.

## Slippage gate
For each clock independently, reprice both SHORT fills adversely at:
- 0 bps/fill
- 2 bps/fill
- 5 bps/fill
- 10 bps/fill

At 5 bps per fill, execution robustness is SUPPORTED iff:
- WR >= 65%
- PF >= 1.50
- net > 0

No slippage threshold may be relaxed post-result.

## Raw 5m parity gate
For each clock independently:

1. Rebuild every eligible session from frozen reference bars and causal raw bar-open/bar-close events using the shadow-safe F15 state machine.
2. Compare against the frozen B27DR canonical stream for that exact clock.
3. Require exact signal count, exact `(partition, entry timestamp)` identity/order, and exact geometry for entry price, H, L, range, F15, F65, E20_DOWN, confirmation bar, and touch elapsed time.

Raw parity is SUPPORTED only with **zero missing signals, zero extra signals, and zero geometry mismatches**.

If a future-dependent historical veto is exposed, live logic must not be modified to reproduce the look-ahead. The affected clock is not considered a B27DY survivor unless a separate causal correction/rescore is completed.

## Survivor definition
An additional clock survives B27DY only if ALL are true independently:

- chronological stability SUPPORTED;
- portfolio compatibility SUPPORTED;
- 5 bps/fill execution robustness SUPPORTED;
- raw 5m signal parity SUPPORTED.

No ranking among failed clocks and no parameter rescue are permitted.

## Survivor basket projection
After individual gates are frozen and scored:

- take only clocks that independently survive;
- combine them with existing validated `SHORT_2000`;
- merge with frozen pre-B27DX B27DQ LONG candidates;
- apply the same global one-BTC-position chronological lock;
- report total N, LONG N, SHORT N, WR, PF, net, and incremental N/net versus the existing LONG+SHORT20 pre-correction control (N=283; net about +$367.49).

The survivor basket is a projection/portfolio validation, not a new selection gate and not live authorization.

## Hard guardrails
- Do not change any strategy parameter.
- Do not search additional clocks.
- Do not drop losing trades.
- Do not rescue a failed clock with filters.
- Do not modify legacy live exchange entry code.
- B27DX causal LONG correction remains a separate prerequisite before final live hardcoding.
