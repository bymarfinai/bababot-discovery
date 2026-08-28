# BNB Temporal A1 — B27EZ Preregistration

Status: preregistered before result reveal.

## Objective
Replicate the BTC Temporal A1 discovery method on BNB without forcing one entry/TP/SL geometry across clock zones. Find repeatable BNB weekday × hour temporal priors first; entry logic is deferred to a later milestone.

## Data
- Symbol: BNBUSDT.
- Source: existing raw Binance 5m history loaded through the frozen repository loader.
- Discovery partition only: 2022-01-01 00:00 UTC through 2025-01-01 00:00 UTC exclusive.
- External 2020-2021, reference-validation 2025-01-01 through 2026-07-30, and August 2026 are not used or revealed.
- Resample completed 5m bars to causal 15m OHLC bars; require all 3 constituent 5m bars.
- Timezone for temporal slots: Asia/Jakarta / WIB (UTC+7), matching BTC Temporal A1 convention.

## Frozen A1 scan
- Scan all 7 weekdays × 24 local clock-hours = 168 slots.
- Observation/entry proxy = open of the exact WIB clock-hour 15m bar.
- Horizons: 15m, 30m, 60m, 120m, 240m.
- For each slot × horizon, direction is selected independently from discovery observations: BUY if positive forward-close returns >= negative returns; otherwise SELL.
- Directional WR is measured from signed horizon return.
- MFE and MAE are measured within the same forward horizon from the clock-hour open.
- Symmetric first-touch geometry is measured independently at 0.3%, 0.5%, 0.8%, and 1.0% from the entry proxy.
- If favorable and adverse levels are both touched in the same 15m bar, first-touch result is AMBIGUOUS and excluded from decisive WR.
- Stability: 8 chronological blocks across the development partition.
- No EMA, session/K1/H2 structure, Micro-HL, volume, HOD/LOD, regime, weekday filter beyond the scanned slot, repair logic, fee, slippage, fixed TP, fixed SL, or live-trading changes.

## Ranking
Report both:
1. Raw-WR leaderboard across slot × horizon rows with N >= 120.
2. Stability-first leaderboard using one best horizon per weekday/hour, ranked by: blocks >=65%, then blocks >=60%, then blocks >50%, then median block WR, headline WR, MFE/MAE.

A discovery candidate is interesting if it has meaningful sample, repeated chronological support, and useful excursion/first-touch geometry. No candidate is validated or production-ready in B27EZ.

## Stop rule
STOP after BNB Temporal A1 discovery. Do not create A2 entry sequences, tune filters, reveal any holdout, or integrate live trading in this milestone.
