# B27EY — BNB Native Time-Zone / Session Window Discovery — Preregistration

## Purpose
Test whether BNB has a materially different intraday habitat from the prior London→NY lineage before doing any more loss-repair tuning.

This milestone is **development discovery only**. It does not validate or promote a live setup.

## Data partition
- Pair: `BNBUSDT`, 5m.
- Discovery only: `[2022-01-01, 2025-01-01)` UTC.
- **Do not reveal/use** external 2020–2021, reference-validation 2025–2026-07-30, August 2026, SHORT, or live data.

## Coarse time scan — fixed before reveal
Use six non-overlapping 4h UTC reference blocks. The immediately following 4h block is the execution block.

| ID | Reference UTC | Execution UTC |
|---|---|---|
| Z00 | 00:00–04:00 | 04:00–08:00 |
| Z04 | 04:00–08:00 | 08:00–12:00 |
| Z08 | 08:00–12:00 | 12:00–16:00 |
| Z12 | 12:00–16:00 | 16:00–20:00 |
| Z16 | 16:00–20:00 | 20:00–24:00 |
| Z20 | 20:00–24:00 | 00:00–04:00 next UTC day |

No 1h/2h sliding optimization is allowed in B27EY.

## Frozen structure within each zone
For each UTC date + zone:
1. `H=max(high)` and `L=min(low)` over the 4h reference block; `R=H-L`.
2. Execution begins at the next block open.
3. SEEK_K1:
   - high-side visit candle: `high >= H && close <= H`.
   - low-side visit candle: `low <= L && close >= L`.
   - `close > H` before K1 = break-before-K1; `close < L` before K1 = opposite break.
   - same-candle high+low ambiguity is excluded.
   - K1 is the first high-side visit only if zero prior low-side visits occurred in the execution block.
4. K1 episode continues while `high >= H && close <= H`.
5. Causal leave = first later candle that is not part of the same high-touch episode.
6. AFTER_LEAVE terminal ordering:
   - H2 if `high >= H`.
   - opposite break if `close < L`.
   - same-bar H2 + opposite break = ambiguous and excluded.

## Frozen entry
Use the already-defined `E5_MICRO_HL_BULL` idea, recreated causally inside each zone:
- after causal leave and before terminal H2/opposite-break,
- completed 5m signal bar must satisfy:
  - `low > previous low`,
  - `close > previous close`,
  - `close > open`.
- signal bar is owned by the structural terminal; therefore if H2/opposite-break occurs on the signal bar, no entry.
- entry = next 5m open, only if it exists before execution block end.

No extra filters.

## Frozen economics
- TP = `H + 0.30R`.
- SL = `entry - 0.30R`.
- total completed-trade cost = existing repo convention `0.15%` (fee + slippage).
- TP/SL active on entry bar.
- if TP and SL touch in the same 5m bar, SL wins.
- if neither hits by execution end, exit at final completed 5m close.
- illustrative notional only: $500/trade, inherited from B27ES.

## Metrics by zone
Report at minimum:
- sessions,
- K1 count,
- causal leaves,
- upstream H2 rate after leave,
- E5 entries,
- structural H2-after-entry rate,
- actual TP/SL net WR,
- average net return/trade,
- total illustrative PnL @ $500,
- profit factor,
- maximum drawdown,
- median geometric RR,
- yearly 2022/2023/2024 trade count, WR, PF.

## Ranking — WR first
Primary ranking among zones with `N >= 30` actual trades:
1. highest actual net TP/SL WR,
2. then PF,
3. then average net return,
4. then larger N.

Definitions:
- **70% candidate**: `N>=30`, actual net WR `>=70%`, PF `>1.0`.
- **near candidate**: `N>=30`, actual net WR `>=65%`, PF `>1.0`.

These labels are discovery labels only, not validation.

## Integrity
- No retuning after results are revealed.
- No sliding-hour search.
- No combining zones.
- No loss-repair rules from B27ET–B27EX.
- Structural H2 rates must never be called trading WR.

STOP after development discovery and persist outputs.