# BNB LONG Reset V1 — H02 Trade Construction PREREG

Status: **FROZEN BEFORE DEVELOPMENT CONSTRUCTION RESULTS**

## Frozen structural signal

The structural signal is immutable in this stage:
- Symbol: **BNBUSDT perpetual**
- Side: **LONG only**
- Habitat: **02:00–03:00 WIB**
- Anchors: **02:00 / 02:15 / 02:30 / 02:45 WIB**
- Primary: **`rv_ratio_60_240__HIGH`**
- Secondary: **`efficiency_60m__HIGH`**
- HIGH boundary: causal percentile **>= 2/3** using the previous 60 same-anchor observations, minimum history 40
- Feature information: completed 5m bars strictly before the anchor
- Reference entry: 5m **open at the anchor**

The structural OOS result is already known, but **construction selection is Development-only**. OOS 2025-01-01 through 2026-07-30 may not be used to select, rank, rescue, or alter an exit rule, overlap rule, cost assumption, threshold, anchor, or feature.

## Development construction sample

- Selection period: **2022-01-01 through 2024-12-31 WIB only**
- Existing structural signal engine must be reused without modification.
- No H03+ discovery, no new feature search, and no anchor removal are permitted.

## Executability / overlap rule

Frozen rule: **ONE_POSITION / NO STACKING**.

Signals are processed chronologically. If a LONG position is still open, later structural signals are skipped until that position has exited. There is no pyramiding or simultaneous H02 position.

For a scheduled time exit at an exact anchor timestamp, the existing position exits first and a new qualifying signal at that same timestamp may enter. For an intrabar TP/SL exit, the position is considered occupied through that 5m bar.

Skipped overlap signals must be reported.

## Frozen candidate set

Only the following **29** construction candidates are allowed.

### A. Time exits — 5 candidates

Market exit at the exact future 5m open after:
- 60 minutes
- 120 minutes
- 180 minutes
- 240 minutes
- 360 minutes

### B. Fixed TP/SL with time stop — 24 candidates

TP distance:
- 0.60%
- 0.90%
- 1.20%
- 1.50%

SL distance:
- 0.60%
- 0.90%
- 1.20%

Maximum hold:
- 240 minutes
- 360 minutes

Cartesian product = **4 × 3 × 2 = 24 candidates**.

For LONG trades, TP/SL evaluation uses 5m OHLC from the entry bar onward but strictly before the time-stop bar. If TP and SL are both touched in the same 5m bar, use **adverse-first / SL first**. If neither barrier is hit, exit at the exact max-hold future 5m open.

No trailing stop, breakeven rule, partial take profit, dynamic TP/SL, anchor-specific rule, regime-specific rule, or discretionary exit is permitted in this stage.

## Frozen reference cost model

Construction selection is based on **net return after 0.12% round-trip modeled trading friction**:
- fee allowance: 0.05% per side
- slippage allowance: 0.01% per side
- total modeled round trip: **0.12% of notional**

This is a conservative research reference model, not a claim about the user's account-specific Binance fee tier.

Dollar translations use fixed **$500 notional per executed trade** only for comparability. Leverage, margin mode, liquidation distance, and position sizing are **not selected here**; those belong to Execution Validation.

## Metrics

For every candidate report at minimum:
- structural signals available
- executed trades
- skipped overlap signals
- trades/week over full 2022–2024 span
- gross WR / mean / PF
- net WR / mean / PF after frozen cost
- net cumulative equivalent at $500 notional
- net max drawdown at $500 notional
- max net loss streak
- 2022 / 2023 / 2024 net N, WR, mean, PF
- 12-quarter net breakdown
- executed-trade anchor distribution
- exit-reason distribution

## Mandatory Development construction gate

A candidate passes only if **all** conditions are true:

Pooled:
- executed N >= **180**
- frequency >= **1.00 executed trade/week** over the full Development span
- net mean return > **0**
- net PF >= **1.15**
- max net loss streak <= **12**

Each calendar year 2022 / 2023 / 2024:
- N >= **50**
- net mean return > **0**
- net PF >= **1.02**

Quarter consistency:
- at least **8/12** calendar quarters have positive net mean return
- every calendar year has at least **2/4** positive-net quarters

Max drawdown is reported and used in deterministic ranking, but no post-hoc DD threshold may be invented after results are seen.

## Deterministic selection ranking

Among full-gate passers, select exactly one by:
1. highest minimum yearly net mean return;
2. highest minimum yearly net PF;
3. highest count of positive-net quarters;
4. highest pooled net PF;
5. highest pooled net mean return;
6. lowest net max drawdown;
7. lower rule complexity — time exit preferred over TP/SL only if all previous ranking fields are tied;
8. lexical rule name tie-break.

No headline-WR ranking is allowed.

## Development construction verdict

- **CONSTRUCTION_PASS**: at least one candidate passes; select exactly one rule using the ranking above and freeze it before executable OOS validation.
- **CONSTRUCTION_FAIL**: no candidate passes. Persist the full failure map and stop. Do not loosen gates, add filters, delete 02:30, optimize costs, or inspect OOS to rescue the rule.
- **INSUFFICIENT_DATA**: data integrity or exact-exit availability prevents a valid verdict.

If CONSTRUCTION_PASS, the selected rule is not yet READY TO TRADE. It must next undergo a separately preregistered executable OOS construction check and then Execution Validation.

Research/shadow only.
