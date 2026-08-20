# BabaBot Research Registry — AMD / FVG Track

Purpose: prevent repeating or renaming accumulation-manipulation-distribution and FVG sequence studies.

## AMD1 — H1 Accumulation -> first-session Manipulation -> exact 3-candle opposite FVG -> Distribution — REJECT

Frozen design:
- BTCUSDT USD-M perpetual;
- completed 1H candles only;
- fixed session opens only: Asia 00:00 UTC / 07:00 WIB, London 07:00 UTC / 14:00 WIB, New York 13:00 UTC / 20:00 WIB;
- accumulation = exactly three completed H1 bars immediately before session open;
- manipulation = first H1 session candle only;
- bearish candidate: high sweeps accumulation high, no low sweep, closes back inside range -> SHORT;
- bullish candidate: low sweeps accumulation low, no high sweep, closes back inside range -> LONG;
- FVG triplet fixed as manipulation candle + next two H1 candles;
- bearish FVG requires middle candle bearish and `high(third) < low(manipulation)`;
- bullish FVG requires middle candle bullish and `low(third) > high(manipulation)`;
- no later FVG search, no minimum gap/body/ATR/EMA/volume/OI/taker filter;
- AMD baseline entry = next H1 open after manipulation;
- AMD+FVG entry = next H1 open after third FVG candle closes;
- structural SL = manipulation extreme;
- TP sized for modeled net RR1:1 after 0.15% round-trip fee; max hold 6H; same-hour ambiguity adverse-first.

Evidence coverage: 2020-01-01 through available 2026-08-18 completed H1 archive, 58,128 rows.
Manipulation events: 2,157. Exact FVG confirmations: 253, conversion 11.73%.

Aggregate +3H directional rate:
- reference development: AMD baseline N1031 54.22%; AMD+FVG N125 52.00%;
- reference validation: baseline N443 52.82%; FVG N47 55.32%;
- untouched external 2020-2021: baseline N661 51.44%; FVG N79 50.63%;
- August 2026 available data: baseline N21 61.90%; FVG N2 0.00%.

External FVG blocks: 47.37%, 45.00%, 65.00%, 45.00% +3H. No stable directional support.

Fixed validation cells that appeared high-WR were too small and failed transfer:
- ASIA_OPEN SHORT FVG validation 4/5 = 80.00%, external 7/12 = 58.33%;
- NEW_YORK_OPEN SHORT FVG validation 8/10 = 80.00%, external 8/16 = 50.00%.
These are explicitly non-promotable and must not be isolated post-hoc.

Executable net-RR1:1 was substantially worse after waiting for the exact FVG:
- validation FVG N47 decisive WR19.15%, PnL -$226.20, expectancy -$4.81/trade, median structural risk 1.09%;
- external FVG N79 decisive WR16.46%, PnL -$786.02, expectancy -$9.95/trade, median structural risk 1.99%;
- August FVG N2, WR0%, PnL -$11.83.

Verdicts:
- `AMD1_FVG_DIRECTION_SUPPORTED=FAIL`
- `AMD1_80_CANDIDATE=FAIL`
- `AMD1_EXECUTION_SUPPORTED=FAIL`

Interpretation: the exact screenshot-style sequence (3H accumulation, first-session sweep/reclaim, immediate opposite H1 FVG, then entry) is rare and does not robustly improve directional accuracy. Waiting three H1 bars for a strict FVG materially worsens structural entry geometry: price is often already far from the manipulation extreme, expanding the stop distance and making net 1:1 execution poor.

Do not rescue AMD1 by post-hoc isolating Asia/NY SHORT, loosening the FVG definition, searching later FVGs, changing accumulation length, adding minimum FVG size, or retuning execution on the same evidence. Any future AMD/FVG study must use a materially different causal mechanism and be preregistered independently.
