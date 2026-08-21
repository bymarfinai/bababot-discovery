# BTC Weekly-100 Causal Search W100-V1 — Preregistration

Status: **FROZEN BEFORE RESULT**

Purpose: search for a genuinely causal BTC setup with approximately one trade per week and minimum modeled net RR 1:1, without selecting the best trade after a week has completed.

## Market / source
- BTCUSDT USD-M perpetual.
- Official completed Binance Futures H1 source used by existing research, coverage 2020 onward.
- Test both native H1 and UTC-aligned H4 aggregated from four completed H1 bars.

## Opportunity definition
For each timeframe independently:
- Reference bar = completed bar `i`.
- Trigger bar = completed bar `i+1`.
- CLASSIC breakout only:
  - LONG if trigger close > reference high;
  - SHORT if trigger close < reference low.
- Entry = next bar open (`i+2`).
- `range = reference high - reference low`.
- `extension = distance of trigger close beyond broken reference boundary / range`.
- `body_ratio = abs(trigger close-trigger open)/(trigger high-trigger low)`.
- Frozen ranking score = `extension * body_ratio`.
- No failed-break family, volume, ATR, weekday, session, side, trend, or other filter.

## Development-only frequency calibration
- External untouched: 2020-01-01 through 2021-12-31.
- Development: 2022-01-01 through 2024-12-31.
- Reference validation: 2025-01-01 through 2026-07-29.
- August diagnostic: 2026-08-01 through available completed archive.
- For each timeframe separately, derive exactly one score threshold from DEVELOPMENT ONLY.
- Let `W` = number of ISO weeks represented in development and `M` = number of development opportunities.
- Frozen threshold is the empirical quantile `q = max(0, 1 - W/M)` of development score, chosen without trade outcomes, targeting roughly one above-threshold raw opportunity per week.
- Threshold is then frozen and applied unchanged to external, validation, and August.

## Causal weekly selection
- In each ISO week, consider above-threshold opportunities in chronological order.
- Select **the first** above-threshold opportunity only; ignore all later opportunities in that week.
- Therefore selection is knowable live and maximum frequency is one trade per ISO week.
- No retrospective weekly ranking/top-1 selection.

## Execution
- Structural SL distance = exactly one reference-bar range from entry, opposite trade direction.
- TP raw distance = structural risk fraction + 0.0030 of entry, so modeled net reward equals modeled net loss after 0.15% round-trip fee.
- Thus modeled net RR = 1:1.
- H1 max hold = 6 completed H1 bars.
- H4 max hold = 6 completed H4 bars / 24H.
- Same-bar TP+SL ambiguity = adverse-first / SL.
- TIME exits at final frozen hold-bar close.
- Reference notional = $500 for PnL diagnostics.

## Required reporting
For H1 and H4, by partition:
- raw opportunity count;
- frozen score threshold;
- selected N and selected trades/week;
- TP / SL / TIME;
- decisive WR and all-trade positive-return WR;
- PnL, expectancy, PF;
- chronological blocks;
- exact weeks traded and weeks with no trade.

## Gates
`W100V1_ROBUST_100_FOUND=PASS` only if at least one timeframe has:
- external selected N >= 20 and decisive WR = 100%;
- reference-validation selected N >= 20 and decisive WR = 100%;
- positive total PnL in both external and validation;
- at least 3 positive chronological blocks in both external and validation.

`W100V1_HIGH_PRECISION_CANDIDATE=PASS` if a timeframe has external and validation decisive WR >=80%, N>=20 in each, positive PnL in both, and >=3 positive blocks in both.

## Anti-rescue lock
After results do not tune score threshold, quantile target, weekday/session/side, breakout definition, SL/TP, hold, or choose second/third weekly opportunities. Any follow-up must be independently preregistered.